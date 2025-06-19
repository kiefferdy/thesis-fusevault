import { useState, useEffect } from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Box, 
  IconButton, 
  Drawer, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText,
  useMediaQuery,
  useTheme,
  Chip,
  Tooltip
} from '@mui/material';
import { 
  Menu as MenuIcon, 
  Dashboard, 
  CloudUpload, 
  History, 
  Person, 
  Home,
  CloudOff,
  VpnKey,
  Block
} from '@mui/icons-material';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import WalletButton from './WalletButton';
import { useAuth } from '../contexts/AuthContext';
import useApiKeysStatus from '../hooks/useApiKeysStatus';

function NavBar() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { isAuthenticated, validateSessionNow } = useAuth();
  const { isDisabled: apiKeysDisabled, isEnabled: apiKeysEnabled } = useApiKeysStatus({
    pollingInterval: 0, // Disable polling in NavBar
    refetchOnFocus: true // But still refresh on window focus
  });
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Debug logging
  useEffect(() => {
    console.log('NavBar - API Keys Status:', { 
      disabled: apiKeysDisabled, 
      enabled: apiKeysEnabled
    });
  }, [apiKeysDisabled, apiKeysEnabled]);

  const navigationItems = [
    { text: 'Home', icon: <Home />, path: '/', requiresAuth: false },
    { text: 'Dashboard', icon: <Dashboard />, path: '/dashboard', requiresAuth: true },
    { text: 'Upload', icon: <CloudUpload />, path: '/upload', requiresAuth: true },
    { text: 'History', icon: <History />, path: '/history', requiresAuth: true },
    { text: 'Profile', icon: <Person />, path: '/profile', requiresAuth: true },
    { text: 'API Keys', icon: <VpnKey />, path: '/api-keys', requiresAuth: true },
  ];

  const filteredItems = navigationItems.filter(item => 
    !item.requiresAuth || (item.requiresAuth && isAuthenticated)
  );

  const toggleDrawer = (open) => (event) => {
    if (event && event.type === 'keydown' && (event.key === 'Tab' || event.key === 'Shift')) {
      return;
    }
    setDrawerOpen(open);
  };

  const isActivePath = (path) => {
    return location.pathname === path;
  };

  // Handle navigation with session validation for protected routes
  const handleNavigate = async (path, requiresAuth) => {
    if (requiresAuth && isAuthenticated) {
      // Validate session before navigating to protected route
      const isValid = await validateSessionNow();
      if (!isValid) {
        // Session validation will handle the logout and redirect
        return;
      }
    }
    navigate(path);
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          {isMobile && (
            <IconButton
              size="large"
              edge="start"
              color="inherit"
              aria-label="menu"
              sx={{ mr: 2 }}
              onClick={toggleDrawer(true)}
            >
              <MenuIcon />
            </IconButton>
          )}
          
          <Typography 
            variant="h6" 
            component={Link} 
            to="/" 
            sx={{ 
              flexGrow: 1, 
              textDecoration: 'none', 
              color: 'inherit',
              fontWeight: 'bold'
            }}
          >
            FuseVault
          </Typography>
          
          
          {!isMobile && (
            <Box sx={{ display: 'flex', gap: 2, mx: 2 }}>
              {filteredItems.map((item) => (
                <Box
                  key={item.text}
                  onClick={() => handleNavigate(item.path, item.requiresAuth)}
                  sx={{ 
                    textDecoration: 'none', 
                    color: 'white',
                    py: 1,
                    px: 2,
                    borderRadius: 1,
                    backgroundColor: isActivePath(item.path) ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    position: 'relative',
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: 'rgba(255, 255, 255, 0.1)'
                    }
                  }}
                >
                  {item.icon}
                  <Typography>{item.text}</Typography>
                  {/* Show disabled indicator for API Keys */}
                  {item.path === '/api-keys' && apiKeysDisabled && (
                    <Tooltip title="API Keys feature is disabled">
                      <Block sx={{ fontSize: 16, color: 'orange', ml: 0.5 }} />
                    </Tooltip>
                  )}
                </Box>
              ))}
            </Box>
          )}
          
          <WalletButton />
        </Toolbar>
      </AppBar>
      
      {/* Mobile Drawer */}
      <Drawer
        anchor="left"
        open={drawerOpen}
        onClose={toggleDrawer(false)}
      >
        <Box
          sx={{ width: 250 }}
          role="presentation"
          onClick={toggleDrawer(false)}
          onKeyDown={toggleDrawer(false)}
        >
          
          <List>
            {filteredItems.map((item) => (
              <ListItem 
                button 
                key={item.text} 
                onClick={() => handleNavigate(item.path, item.requiresAuth)}
                selected={isActivePath(item.path)}
              >
                <ListItemIcon>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} />
                {/* Show disabled indicator for API Keys */}
                {item.path === '/api-keys' && apiKeysDisabled && (
                  <Tooltip title="API Keys feature is disabled">
                    <Block sx={{ fontSize: 20, color: 'orange' }} />
                  </Tooltip>
                )}
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
    </Box>
  );
}

export default NavBar;