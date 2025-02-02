import dotenv from 'dotenv';
import { create } from '@web3-storage/w3up-client';
import { filesFromPaths } from 'files-from-path';
import fetch from 'node-fetch';

dotenv.config({ path: '../.env' });

async function initializeClient() {
  const DID_KEY = process.env.WEB3_STORAGE_DID_KEY;
  const EMAIL = process.env.WEB3_STORAGE_EMAIL;
  if (!DID_KEY) {
    throw new Error('WEB3_STORAGE_DID_KEY is not defined in the environment variables.');
  }
  if (!EMAIL) {
    throw new Error('WEB3_STORAGE_EMAIL is not defined in the environment variables.');
  }

  const client = await create();
  await client.login(EMAIL);
  await client.setCurrentSpace(DID_KEY);

  console.log('Space successfully set!');
  return client;
}

/**
 * Upload one file (by path) to Web3.Storage.
 */
export async function uploadFile(filePath) {
  try {
    const client = await initializeClient();
    const files = await filesFromPaths([filePath]);
    const fileCid = await client.uploadFile(files[0]);

    console.log(`File uploaded successfully. CID: ${fileCid}`);
    console.log(`Access file at: https://${fileCid}.ipfs.w3s.link`);
    return fileCid;
  } catch (error) {
    console.error('Error uploading file:', error);
    throw error;
  }
}

/**
 * Build a gateway URL for the given CID.
 */
export async function getFileUrl(cid) {
  return `https://${cid}.ipfs.w3s.link`;
}

/**
 * Fetch the file contents from IPFS and return as text.
 */
export async function displayFileContents(cid) {
  try {
    const fileUrl = await getFileUrl(cid);
    const response = await fetch(fileUrl);
    if (!response.ok) {
      throw new Error(`Failed to fetch file: ${response.statusText}`);
    }
    const fileContents = await response.text();
    console.log(`Contents of the file:\n${fileContents}`);
    return fileContents;
  } catch (error) {
    console.error('Error displaying file contents:', error);
    throw error;
  }
}
