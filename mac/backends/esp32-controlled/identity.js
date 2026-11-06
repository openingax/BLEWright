import { parseAdvertisement } from "../esp32-scan/advertisement.js";
export function validateAllow(allow) {
  if (
    !allow ||
    typeof allow.address !== "string" ||
    !/^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$/i.test(allow.address) ||
    ![0, 1].includes(allow.addressType)
  )
    throw Error("EXACT_C6_ALLOW_REQUIRED");
  const nonce =
    typeof allow.nonce === "string" && /^[0-9a-f]{8}$/i.test(allow.nonce)
      ? Array.from(Buffer.from(allow.nonce, "hex"))
      : allow.nonce;
  if (
    !Array.isArray(nonce) ||
    nonce.length !== 4 ||
    !nonce.every((x) => Number.isInteger(x) && x >= 0 && x <= 255)
  )
    throw Error("EXACT_C6_NONCE_REQUIRED");
  return Object.freeze({
    address: allow.address.toUpperCase(),
    addressType: allow.addressType,
    nonce: Object.freeze([...nonce]),
  });
}
export class IdentityGate {
  constructor(allow, { now = () => Date.now(), maxAgeMs = 30000 } = {}) {
    this.allow = validateAllow(allow);
    this.now = now;
    this.maxAgeMs = maxAgeMs;
    this.observedAt = null;
  }
  observe(event) {
    if (
      event.event !== "advertisement" ||
      event.address?.toUpperCase() !== this.allow.address ||
      event.addressType !== this.allow.addressType
    )
      return;
    const data = parseAdvertisement(event.advertising).manufacturerData;
    if (!data) return;
    const expected = [255, 255, ...this.allow.nonce];
    this.observedAt =
      data.length === expected.length && data.every((b, i) => b === expected[i])
        ? this.now()
        : null;
  }
  assertConnect(address, addressType = this.allow.addressType) {
    if (
      typeof address !== "string" ||
      address.toUpperCase() !== this.allow.address ||
      addressType !== this.allow.addressType
    )
      throw Error("TARGET_NOT_ALLOWED");
    if (
      this.observedAt === null ||
      this.now() - this.observedAt > this.maxAgeMs
    )
      throw Error("C6_ADVERTISEMENT_PROOF_REQUIRED");
  }
}
