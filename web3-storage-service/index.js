import express from 'express';
import multer from 'multer';
import fs from 'fs/promises';
import { uploadFile, getFileUrl, displayFileContents } from './backend.js';

const app = express();
const PORT = 8080;

/**
 * Configure multer for disk storage in 'upload_queue/'.
 */
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'upload_queue/');
  },
  filename: (req, file, cb) => {
    const uniqueName = `${Date.now()}-${file.originalname}`;
    cb(null, uniqueName);
  }
});

const upload = multer({ storage });

/**
 * POST /upload
 * Accept multiple files, each stored in 'upload_queue/'.
 * Then upload them all to Web3.Storage, delete them locally, and return an array of CIDs.
 */
app.post('/upload', upload.array('files'), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ error: 'No file(s) uploaded' });
    }

    // Array to store { filename, cid } for each uploaded file
    const cids = [];

    for (const file of req.files) {
      const filePath = file.path;
      try {
        // Upload file to Web3.Storage and get returned CID
        const fileCid = await uploadFile(filePath);
        cids.push({
          filename: file.originalname,
          cid: fileCid
        });
      } catch (error) {
        console.error('Error uploading file:', file.originalname, error);
        throw error;
      } finally {
        // Remove the file from local disk whether upload succeeds or fails
        try {
          await fs.unlink(filePath);
        } catch (err) {
          console.error('Error deleting local file:', file.originalname, err);
        }
      }
    }

    // Return an array of cids so the client knows what got uploaded
    return res.json({ cids });

  } catch (error) {
    console.error('Error handling file upload:', error);
    return res.status(500).json({ error: error.message });
  }
});

/**
 * GET /file/:cid
 * Retrieve the public gateway URL for a given CID.
 */
app.get('/file/:cid', async (req, res) => {
  try {
    const url = await getFileUrl(req.params.cid);
    return res.json({ url });
  } catch (error) {
    console.error('Error retrieving file URL:', error);
    return res.status(500).json({ error: error.message });
  }
});

/**
 * GET /file/:cid/contents
 * Fetch the file contents from IPFS.
 */
app.get('/file/:cid/contents', async (req, res) => {
  try {
    const contents = await displayFileContents(req.params.cid);
    return res.send(contents);
  } catch (error) {
    console.error('Error displaying file contents:', error);
    return res.status(500).json({ error: error.message });
  }
});

// Start Express server
app.listen(PORT, () => {
  console.log(`API server running on http://localhost:${PORT}`);
});
