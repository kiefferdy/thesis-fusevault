import express from 'express';
import multer from 'multer';
import fs from 'fs';
import { uploadFile, getFileUrl, displayFileContents } from './backend.js';
import { computeCID } from './utilities.js';

const app = express();
const PORT = process.env.PORT || 8080;
const UPLOAD_DIR = 'upload_queue';

// Determine host binding based on environment
// Railway requires IPv6 (::) for private networking, localhost uses IPv4 (0.0.0.0)
const HOST = process.env.RAILWAY_ENVIRONMENT_NAME ? '::' : '0.0.0.0';
if (!fs.existsSync(UPLOAD_DIR)) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

/**
 * Configure multer for disk storage in 'upload_queue/'.
 */
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, UPLOAD_DIR);
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
          await fs.promises.unlink(filePath);
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

/**
 * GET /health
 * Health check endpoint.
 */
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString()
  });
});

// Start Express server
app.listen(PORT, HOST, () => {
  console.log(`Web3.Storage service running on ${HOST}:${PORT}`);
});

/**
 * POST /calculate-cid
 * New endpoint that calculates the exact IPFS CID for a given file using ipfs-only-hash.
 */
app.post('/calculate-cid', upload.single('file'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }
  
  const filePath = req.file.path;
  try {
    const cid = await computeCID(filePath);
    res.json({ computed_cid: cid });
  } catch (error) {
    console.error('Error calculating CID:', error);
    res.status(500).json({ error: error.message });
  } finally {
    // Clean up the uploaded file
    try {
      await fs.promises.unlink(filePath);
    } catch (err) {
      console.error('Error deleting uploaded file:', err);
    }
  }
});
