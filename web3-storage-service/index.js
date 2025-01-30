import express from 'express';
import multer from 'multer';
import { uploadFile, getFileUrl, displayFileContents } from './backend.js';

const app = express();
const PORT = 5000;
const upload = multer({ dest: 'upload_queue/' });

// Upload file endpoint
app.post('/upload', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }
        const result = await uploadFile(req.file.path);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get file URL endpoint
app.get('/file/:cid', async (req, res) => {
    try {
        const url = await getFileUrl(req.params.cid);
        res.json({ url });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Fetch file contents
app.get('/file/:cid/contents', async (req, res) => {
    try {
        const contents = await displayFileContents(req.params.cid);
        res.send(contents);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Start Express server
app.listen(PORT, () => {
    console.log(`API server running on http://localhost:${PORT}`);
});
