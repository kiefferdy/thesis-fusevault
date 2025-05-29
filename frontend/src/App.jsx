import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { Toaster } from 'react-hot-toast';
import { useEffect } from 'react';

// Context Providers
import { AuthProvider } from './contexts/AuthContext';

// Debug utilities
import { setupDebugHelpers } from './utils/debugUtils';

// Components
import NavBar from './components/NavBar';

// Pages
import HomePage from './pages/HomePage';
import DashboardPage from './pages/DashboardPage';
import UploadPage from './pages/UploadPage';
import AssetDetailPage from './pages/AssetDetailPage';
import HistoryPage from './pages/HistoryPage';
import ProfilePage from './pages/ProfilePage';

// Create a new QueryClient instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Create a theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#1565c0', // Deep blue
    },
    secondary: {
      main: '#7cb342', // Green
    },
  },
  typography: {
    fontFamily: "'Inter', 'Roboto', 'Helvetica', 'Arial', sans-serif",
  },
});

// Auth Guard for protected routes
const ProtectedRoute = ({ children }) => {
  // Check if the user is authenticated client-side first
  const isAuthenticated = localStorage.getItem('isAuthenticated') === 'true';
  
  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  
  return children;
};

function App() {
  // Set up debug helpers in development mode
  useEffect(() => {
    if (import.meta.env.DEV) {
      setupDebugHelpers();
    }
  }, []);
  
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <AuthProvider>
            <NavBar />
            <main>
              <Routes>
                <Route path="/" element={<HomePage />} />
                
                <Route 
                  path="/dashboard" 
                  element={
                    <ProtectedRoute>
                      <DashboardPage />
                    </ProtectedRoute>
                  } 
                />
                
                <Route 
                  path="/upload" 
                  element={
                    <ProtectedRoute>
                      <UploadPage />
                    </ProtectedRoute>
                  } 
                />
                
                <Route 
                  path="/assets/:assetId" 
                  element={
                    <ProtectedRoute>
                      <AssetDetailPage />
                    </ProtectedRoute>
                  } 
                />
                
                <Route 
                  path="/assets/:assetId/edit" 
                  element={
                    <ProtectedRoute>
                      <UploadPage />
                    </ProtectedRoute>
                  } 
                />
                
                <Route 
                  path="/history" 
                  element={
                    <ProtectedRoute>
                      <HistoryPage />
                    </ProtectedRoute>
                  } 
                />
                
                <Route 
                  path="/profile" 
                  element={
                    <ProtectedRoute>
                      <ProfilePage />
                    </ProtectedRoute>
                  } 
                />
                
                {/* Fallback route */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
            <Toaster position="top-right" />
          </AuthProvider>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;