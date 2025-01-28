require('dotenv').config({ path: '../.env' });
const { create, add, list } = require('@web3-storage/w3up-client');
const fs = require('fs');
const path = require('path');

const API_KEY = process.env.W3UP_API_KEY;
if (!API_KEY) {
  throw new Error('W3UP_API_KEY is not set in the .env file');
}

const client = create({ apiKey: API_KEY });

async function uploadFile(filePath) {
  try {
    const fileStream = fs.createReadStream(filePath);
    const cid = await add(client, fileStream, { name: path.basename(filePath) });
    console.log(`File uploaded successfully. CID: ${cid}`);
    return cid;
  } catch (error) {
    console.error('Error uploading file:', error);
    throw error;
  }
}

async function listUploads() {
  try {
    const uploads = await list(client);
    console.log('Uploads:', uploads);
    return uploads;
  } catch (error) {
    console.error('Error listing uploads:', error);
    throw error;
  }
}