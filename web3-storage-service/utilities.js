import fs from 'fs';
import { UnixFS } from '@web3-storage/upload-client';

/**
 * Computes the CID for a file using Web3.Storage's own implementation.
 * This guarantees an exact match with the CIDs that Web3.Storage generates.
 * 
 * @param {string} filePath - The local path to the file.
 * @returns {Promise<string>} - The computed CID (CIDv1 in base32).
 */
export async function computeCID(filePath) {
  try {
    // Read the file
    const buffer = await fs.promises.readFile(filePath);
    
    // Create a blob-like object with a stream method
    const file = {
      stream: () => new ReadableStream({
        start(controller) {
          controller.enqueue(buffer);
          controller.close();
        }
      })
    };
    
    // Use Web3.Storage's own UnixFS encoding to compute the CID
    const { cid } = await UnixFS.encodeFile(file);
    
    return cid.toString();
  } catch (error) {
    throw new Error(`Error computing CID: ${error.message}`);
  }
}
