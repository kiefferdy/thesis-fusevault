import axios from 'axios';

const API_URL = 'http://localhost:8000';

const checkBackendAvailable = async () => {
  try {
    console.log('Testing backend connection...');
    
    // Make a simple request to the backend
    const response = await axios.get(`${API_URL}/auth/nonce/0x0000000000000000000000000000000000000000`, { 
      timeout: 3000 
    });
    
    console.log('Backend response status:', response.status);
    console.log('Backend response data:', response.data);
    
    return true;
  } catch (error) {
    console.error('Error type:', error.constructor.name);
    
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.log('Response status:', error.response.status);
      console.log('Response data:', error.response.data);
      console.log('Response headers:', error.response.headers);
      return true; // Backend is available, just returned an error response
    } else if (error.request) {
      // The request was made but no response was received
      console.log('No response received from backend');
      console.log('Request details:', error.request);
      return false;
    } else {
      // Something happened in setting up the request that triggered an Error
      console.log('Error message:', error.message);
      return false;
    }
  }
};

// Run the test
checkBackendAvailable()
  .then(available => {
    console.log('Backend available:', available);
  })
  .catch(err => {
    console.error('Unexpected error during test:', err);
  });