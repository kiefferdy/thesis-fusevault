import { uploadFile } from './index.js';

(async () => {
    try {
        const cid = await uploadFile('./upload_queue');
        console.log(`Uploaded file CID: ${cid}`);
    } catch (error) {
        console.error('Upload failed:', error);
    }
})();
