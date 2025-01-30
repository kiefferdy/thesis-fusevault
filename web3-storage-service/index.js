import dotenv from 'dotenv';
import { create } from '@web3-storage/w3up-client';
import { filesFromPaths } from 'files-from-path';
import fetch from 'node-fetch';

async function initializeClient() {
    dotenv.config({ path: '../.env' });
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

async function uploadFile(filePath) {
    try {
        const client = await initializeClient();
        const files = await filesFromPaths([filePath]);
        const fileCid = await client.uploadFile(files[0]);
        console.log(`File uploaded successfully. CID: ${fileCid}`);
        console.log(`Access your file at: https://${fileCid}.ipfs.w3s.link`);
        return fileCid;
    } catch (error) {
        console.error('Error uploading file:', error);
    }
}

async function getFileUrl(cid) {
    try {
        return `https://${cid}.ipfs.w3s.link`;
    } catch (error) {
        console.error('Error retrieving file URL:', error);
    }
}

async function displayFileContents(cid) {
    try {
        const fileUrl = await getFileUrl(cid);
        const response = await fetch(fileUrl);
        if (!response.ok) {
            throw new Error(`Failed to fetch file: ${response.statusText}`);
        }
        const fileContents = await response.text();
        console.log(`Contents of the file:
${fileContents}`);
    } catch (error) {
        console.error('Error displaying file contents:', error);
    }
}

export { uploadFile, getFileUrl, displayFileContents };
