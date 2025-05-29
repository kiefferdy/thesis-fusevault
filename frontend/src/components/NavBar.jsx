import { useState } from 'react';
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
  CloudOff
} from '@mui/icons-material';
import { Link, useLocation } from 'react-router-dom';
import WalletButton from './WalletButton';
import { useAuth } from '../contexts/AuthContext';

function NavBar() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { isAuthenticated, backendAvailable } = useAuth();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const navigationItems = [
    { text: 'Home', icon: <Home />, path: '/', requiresAuth: false },
    { text: 'Dashboard', icon: <Dashboard />, path: '/dashboard', requiresAuth: true },
    { text: 'Upload', icon: <CloudUpload />, path: '/upload', requiresAuth: true },
    { text: 'History', icon: <History />, path: '/history', requiresAuth: true },
    { text: 'Profile', icon: <Person />, path: '/profile', requiresAuth: true },
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
          
          {/* Backend status indicator */}
          {isAuthenticated && !backendAvailable && (
            <Tooltip title="Backend server is not available. Running in demo mode.">
              <Chip
                icon={<CloudOff />}
                label="Demo Mode"
                color="warning"
                size="small"
                sx={{ mr: 2 }}
              />
            </Tooltip>
          )}
          
          {!isMobile && (
            <Box sx={{ display: 'flex', gap: 2, mx: 2 }}>
              {filteredItems.map((item) => (
                <Box
                  key={item.text}
                  component={Link}
                  to={item.path}
                  sx={{ 
                    textDecoration: 'none', 
                    color: 'white',
                    py: 1,
                    px: 2,
                    borderRadius: 1,
                    backgroundColor: isActivePath(item.path) ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1
                  }}
                >
                  {item.icon}
                  <Typography>{item.text}</Typography>
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
          {/* Backend status in drawer */}
          {isAuthenticated && !backendAvailable && (
            <Box sx={{ p: 2 }}>
              <Chip
                icon={<CloudOff />}
                label="Demo Mode - Backend Unavailable"
                color="warning"
                size="small"
                sx={{ width: '100%' }}
              />
            </Box>
          )}
          
          <List>
            {filteredItems.map((item) => (
              <ListItem 
                button 
                key={item.text} 
                component={Link} 
                to={item.path}
                selected={isActivePath(item.path)}
              >
                <ListItemIcon>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
    </Box>
  );
}

export default NavBar;