import React from "react";
import { AppBar, Toolbar, Typography, Box, Container } from "@mui/material";
import { Search as SearchIcon } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";

const Header: React.FC = () => {
  const navigate = useNavigate();

  return (
    <AppBar position="static" elevation={2}>
      <Container maxWidth="xl">
        <Toolbar sx={{ justifyContent: "space-between" }}>
          {/* Research Logo */}
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              // cursor: "pointer",
              // "&:hover": { opacity: 0.8 },
            }}
            // onClick={() => navigate("/")}
          >
            <Typography
              variant="h5"
              component="div"
              sx={{
                fontWeight: "bold",
                color: "white",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                letterSpacing: "0.05em",
              }}
            >
              <span style={{ marginRight: "0.1em" }}>rese</span>
              <Box
                component="span"
                sx={{
                  position: "relative",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "1em",
                  height: "1em",
                  margin: "0em -0.2em -0.2em -0.2em",
                }}
              >
                <SearchIcon
                  sx={{
                    fontSize: "0.8em",
                    color: "white",
                  }}
                />
              </Box>
              <span style={{ marginLeft: "0.1em" }}>rch</span>
            </Typography>
          </Box>

          {/* Navigation Links */}
          <Box sx={{ display: "flex", gap: 1 }}></Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
};

export default Header;
