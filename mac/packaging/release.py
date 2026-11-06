#!/usr/bin/env python3
"""Prepare signed Sparkle feed and mirror one PKG to two GitHub Release drafts.
Publish only after notarization. Never pushes source to the public repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
NS = 'http://www.andymatuschak.org/xml-namespaces/sparkle'
ET.register_namespace('sparkle', NS)

def run(*args, capture=False):
    return subprocess.run(args, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout

def make_feed(release, package, signature, notes):
    rss = ET.Element('rss', {'version': '2.0'})
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = 'BLEWright'
    item = ET.SubElement(channel, 'item')
    ET.SubElement(item, 'title').text = 'BLEWright ' + release['version']
    for key, value in [('version', release['build']), ('shortVersionString', release['version']),
                       ('minimumSystemVersion', '13.0'), ('hardwareRequirements', 'arm64')]:
        ET.SubElement(item, f'{{{NS}}}{key}').text = value
    ET.SubElement(item, 'description').text = notes
    ET.SubElement(item, 'enclosure', {
        'url': f"https://github.com/{release['publicRepository']}/releases/download/v{release['version']}/{package.name}",
        'length': str(package.stat().st_size), 'type': 'application/octet-stream',
        f'{{{NS}}}edSignature': signature, f'{{{NS}}}installationType': 'package'})
    return ET.tostring(rss, encoding='utf-8', xml_declaration=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notes', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    release = json.loads((ROOT/'mac/packaging/release.json').read_text())
    package = ROOT/f"dist/BLEWright-{release['version']}-arm64-signed.pkg"
    sign = str(ROOT/'dist/sparkle/bin/sign_update')
    account = release['keyAccount']
    run('pkgutil', '--check-signature', str(package))
    if args.publish:
        run('xcrun', 'stapler', 'validate', str(package))
    key = run(str(ROOT/'dist/sparkle/bin/generate_keys'), '--account', account, '-p', capture=True).strip()
    if key != release['publicKey']:
        raise SystemExit('Sparkle signing key does not match the embedded public key')
    out = ROOT/'dist/release'; out.mkdir(exist_ok=True)
    signature = run(sign, '--account', account, '-p', str(package), capture=True).strip()
    run(sign, '--account', account, '--verify', str(package), signature)
    feed = out/'appcast.xml'
    feed.write_bytes(make_feed(release, package, signature, args.notes.read_text()))
    run(sign, '--account', account, str(feed))
    run(sign, '--account', account, '--verify', str(feed))
    checksum = out/'SHA256SUMS.txt'
    checksum.write_text(f'{hashlib.sha256(package.read_bytes()).hexdigest()}  {package.name}\n')
    if args.prepare_only:
        return
    repositories = [(release['privateRepository'], 'PRIVATE'), (release['publicRepository'], 'PUBLIC')]
    # Validate both destinations before uploading anything.
    for repo, visibility in repositories:
        info = json.loads(run('gh', 'repo', 'view', repo, '--json', 'visibility', capture=True))
        if info['visibility'] != visibility:
            raise SystemExit(f'Unexpected visibility: {repo}')
    tag = 'v' + release['version']
    for repo, _ in repositories:
        existing = subprocess.run(['gh', 'release', 'view', tag, '--repo', repo, '--json', 'isDraft'],
                                  capture_output=True, text=True)
        if existing.returncode == 0:
            if not json.loads(existing.stdout)['isDraft']:
                raise SystemExit(f'Refusing to overwrite a published release: {repo}/{tag}')
        else:
            run('gh', 'release', 'create', tag, '--repo', repo, '--target', 'main', '--draft',
                '--title', 'BLEWright ' + release['version'], '--notes-file', str(args.notes.resolve()))
        run('gh', 'release', 'upload', tag, str(package), str(feed), str(checksum), '--repo', repo, '--clobber')
    if args.publish:
        # Publish private archive first; public latest feed becomes visible last.
        for repo, _ in repositories:
            run('gh', 'release', 'edit', tag, '--repo', repo, '--draft=false', '--latest')
    print('Both releases published' if args.publish else 'Both release drafts uploaded; notarization required before publishing')

if __name__ == '__main__':
    main()
