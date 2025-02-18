import fs from 'fs';
import { of } from 'ipfs-only-hash';

/**
 * Computes the CID for a file using ipfs-only-hash.
 * @param {string} filePath - The local path to the file.
 * @returns {Promise<string>} - The computed CID (CIDv1 in base32).
 */
export async function computeCID(filePath) {
  try {
    const buffer = await fs.promises.readFile(filePath);
    const cid = await of(buffer, { cidVersion: 1 });
    return cid;
  } catch (error) {
    throw new Error(`Error computing CID: ${error.message}`);
  }
}
