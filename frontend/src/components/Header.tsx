import React from "react";
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  Container,
} from "@mui/material";
import {
  Home as HomeIcon,
  Search as SearchIcon,
  Analytics as AnalyticsIcon,
} from "@mui/icons-material";
import { useNavigate, useLocation } from "react-router-dom";

const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { label: "Home", path: "/", icon: <HomeIcon /> },
    { label: "Opportunities", path: "/home", icon: <SearchIcon /> },
    { label: "Enhanced", path: "/enhanced", icon: <AnalyticsIcon /> },
  ];

  return (
    <AppBar position="static" elevation={2}>
      <Container maxWidth="xl">
        <Toolbar sx={{ justifyContent: "space-between" }}>
          {/* Logo/Brand */}
          <Typography
            variant="h6"
            component="div"
            sx={{
              fontWeight: "bold",
              cursor: "pointer",
              "&:hover": { opacity: 0.8 },
            }}
            onClick={() => navigate("/")}
          >
            reSearch
          </Typography>

          {/* Navigation Links */}
          <Box sx={{ display: "flex", gap: 1 }}>
            {navItems.map((item) => (
              <Button
                key={item.path}
                color="inherit"
                startIcon={item.icon}
                onClick={() => navigate(item.path)}
                sx={{
                  backgroundColor:
                    location.pathname === item.path
                      ? "rgba(255,255,255,0.1)"
                      : "transparent",
                  "&:hover": {
                    backgroundColor: "rgba(255,255,255,0.2)",
                  },
                }}
              >
                {item.label}
              </Button>
            ))}
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
};

export default Header;
