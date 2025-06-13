import dotenv from 'dotenv';
import { create } from '@web3-storage/w3up-client';
import { filesFromPaths } from 'files-from-path';
import fetch from 'node-fetch';
import dns from 'dns';
import * as Signer from '@ucanto/principal/ed25519';
import * as Proof from '@web3-storage/w3up-client/proof';
import { StoreMemory } from '@web3-storage/w3up-client/stores/memory';

dotenv.config({ path: './.env' });

// Force IPv4 for DNS resolution on Railway
if (process.env.RAILWAY_ENVIRONMENT_NAME) {
  dns.setDefaultResultOrder('ipv4first');
}

// Global client instance
let clientInstance = null;

async function initializeClient() {
  // Return existing client if already initialized
  if (clientInstance) {
    console.log('Using existing client instance');
    return clientInstance;
  }

  try {
    // Use delegation-based authentication instead of email login
    if (process.env.W3_PRINCIPAL && process.env.W3_PROOF) {
      console.log('Initializing with delegation-based authentication...');
      
      // Parse the principal (private key)
      const principal = Signer.parse(process.env.W3_PRINCIPAL);
      
      // Use in-memory store to avoid persistence issues
      const store = new StoreMemory();
      
      // Create client with specific principal
      clientInstance = await create({ principal, store });
      
      // Parse and add the proof delegation
      const proof = await parseProof(process.env.W3_PROOF);
      const space = await clientInstance.addSpace(proof);
      await clientInstance.setCurrentSpace(space.did());
      
      console.log('Client initialized with delegation successfully!');
      console.log('Current space:', space.did());
      
      return clientInstance;
    }
    
    // Fallback to email-based authentication (for local development)
    console.log('Initializing with email-based authentication...');
    const DID_KEY = process.env.WEB3_STORAGE_DID_KEY;
    const EMAIL = process.env.WEB3_STORAGE_EMAIL;
    
    if (!DID_KEY || !EMAIL) {
      throw new Error('Missing required environment variables for authentication');
    }

    clientInstance = await create();
    await clientInstance.login(EMAIL);
    await clientInstance.setCurrentSpace(DID_KEY);

    console.log('Client initialized with email successfully!');
    return clientInstance;
    
  } catch (error) {
    console.error('Failed to initialize client:', error);
    // Reset client instance on error
    clientInstance = null;
    throw error;
  }
}

/**
 * Parse a base64 identity CID proof using w3up-client
 */
async function parseProof(proofData) {
  try {
    // Use w3up-client's Proof.parse which handles base64 identity CID strings
    return await Proof.parse(proofData);
  } catch (error) {
    console.error('Error parsing proof:', error);
    throw new Error(`Failed to parse proof: ${error.message}`);
  }
}

/**
 * Upload one file (by path) to Web3.Storage with retry logic
 */
export async function uploadFile(filePath, retries = 3) {
  let lastError = null;
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      console.log(`Upload attempt ${attempt}/${retries} for ${filePath}`);
      
      const client = await initializeClient();
      const files = await filesFromPaths([filePath]);
      const fileCid = await client.uploadFile(files[0]);

      console.log(`File uploaded successfully. CID: ${fileCid}`);
      console.log(`Access file at: https://${fileCid}.ipfs.w3s.link`);
      return fileCid;
      
    } catch (error) {
      console.error(`Upload attempt ${attempt} failed:`, error);
      lastError = error;
      
      // Reset client instance on specific errors
      if (error.message?.includes('Unable to resolve') || 
          error.message?.includes('Unauthorized') ||
          error.message?.includes('Failed to parse proof')) {
        console.log('Resetting client instance due to auth error...');
        clientInstance = null;
      }
      
      // Wait before retry (exponential backoff)
      if (attempt < retries) {
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 10000);
        console.log(`Waiting ${delay}ms before retry...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  throw lastError || new Error('Upload failed after all retries');
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