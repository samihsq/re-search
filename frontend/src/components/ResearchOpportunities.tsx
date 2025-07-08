import React, { useState, useEffect } from "react";
import {
  Container,
  Typography,
  Box,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Paper,
} from "@mui/material";
import { Search as SearchIcon } from "@mui/icons-material";
import { apiService, Opportunity } from "../services/api";
import OpportunityCard from "./OpportunityCard";

const ResearchOpportunities: React.FC = () => {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  // Get unique departments and categories for filtering
  const departments = Array.from(
    new Set(opportunities.map((opp) => opp.department).filter(Boolean))
  ).sort();
  const categories = Array.from(
    new Set(opportunities.map((opp) => opp.category).filter(Boolean))
  ).sort();

  useEffect(() => {
    loadOpportunities();
  }, []);

  const loadOpportunities = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiService.getOpportunities({
        limit: 100, // Load first 100 for basic view
        include_inactive: false,
      });
      setOpportunities(result.opportunities);
    } catch (err) {
      console.error("Error loading opportunities:", err);
      setError("Failed to load opportunities. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  // Filter opportunities based on search and filters
  const filteredOpportunities = opportunities.filter((opp) => {
    const matchesSearch =
      searchTerm === "" ||
      opp.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (opp.description &&
        opp.description.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (opp.category &&
        opp.category.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesDepartment =
      departmentFilter === "" || opp.department === departmentFilter;

    const matchesCategory =
      categoryFilter === "" || opp.category === categoryFilter;

    return (
      matchesSearch && matchesDepartment && matchesCategory && opp.is_active
    );
  });

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, textAlign: "center" }}>
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Loading opportunities...
        </Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      {/* <Typography variant="h4" component="h1" gutterBottom>
        Research Opportunities
      </Typography> */}
      {/* <Typography variant="body1" color="text.secondary" paragraph>
        Discover exciting research opportunities across Stanford University.
      </Typography> */}

      {/* Search and Filter Controls */}
      <Paper elevation={1} sx={{ p: 3, mb: 4 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="Search"
              placeholder="Search opportunities..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <SearchIcon sx={{ mr: 1, color: "action.active" }} />
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Department</InputLabel>
              <Select
                value={departmentFilter}
                label="Department"
                onChange={(e) => setDepartmentFilter(e.target.value)}
              >
                <MenuItem value="">All Departments</MenuItem>
                {departments.map((dept) => (
                  <MenuItem key={dept} value={dept}>
                    {dept}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Category</InputLabel>
              <Select
                value={categoryFilter}
                label="Category"
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <MenuItem value="">All Categories</MenuItem>
                {categories.map((cat) => (
                  <MenuItem key={cat} value={cat}>
                    {cat}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Results Summary */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6">
          {filteredOpportunities.length} opportunities found
        </Typography>
        {searchTerm || departmentFilter || categoryFilter ? (
          <Typography variant="body2" color="text.secondary">
            Filtered from {opportunities.length} total opportunities
          </Typography>
        ) : null}
      </Box>

      {/* Opportunities Grid */}
      {filteredOpportunities.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="h6" gutterBottom>
            No opportunities found
          </Typography>
          {/* <Typography color="text.secondary">
            Try adjusting your search criteria or check back later for new
            opportunities.
          </Typography> */}
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {filteredOpportunities.map((opportunity) => (
            <Grid item xs={12} sm={6} lg={4} key={opportunity.id}>
              <OpportunityCard opportunity={opportunity} />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Load More Note */}
      {opportunities.length >= 100 && (
        <Box sx={{ mt: 4, textAlign: "center" }}>
          <Typography variant="body2" color="text.secondary">
            Showing first 100 opportunities. Use the Enhanced View for access to
            all results and advanced search features.
          </Typography>
        </Box>
      )}
    </Container>
  );
};

export default ResearchOpportunities;
