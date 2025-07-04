import React, { useState, useEffect, useCallback } from "react";
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Alert,
  Pagination,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Divider,
  Skeleton,
  Badge,
  Tooltip,
} from "@mui/material";
import {
  AccessTime as AccessTimeIcon,
  LocationOn as LocationIcon,
  School as SchoolIcon,
  Category as CategoryIcon,
  OpenInNew as OpenInNewIcon,
  TrendingUp as TrendingUpIcon,
  Analytics as AnalyticsIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";
import { format, parseISO, isBefore } from "date-fns";
import { apiService, Opportunity, OpportunityStats } from "../services/api";
import EnhancedSearch from "./EnhancedSearch";

interface EnhancedResearchOpportunitiesProps {
  // Optional props for customization
}

const EnhancedResearchOpportunities: React.FC<
  EnhancedResearchOpportunitiesProps
> = () => {
  // State management
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [stats, setStats] = useState<OpportunityStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pagination and filtering
  const [page, setPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(20);
  const [totalItems, setTotalItems] = useState(0);
  const [sortBy, setSortBy] = useState("deadline");
  const [sortOrder, setSortOrder] = useState("asc");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);

  const loadOpportunities = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await apiService.getOpportunities({
        skip: (page - 1) * itemsPerPage,
        limit: itemsPerPage,
        sort_by: sortBy,
        sort_order: sortOrder,
        category: selectedCategory || undefined,
        include_inactive: includeInactive,
      });

      setOpportunities(result.opportunities);
      setTotalItems(result.total);
    } catch (err) {
      setError("Failed to load opportunities. Please try again.");
      console.error("Load opportunities error:", err);
    } finally {
      setLoading(false);
    }
  }, [
    page,
    itemsPerPage,
    sortBy,
    sortOrder,
    selectedCategory,
    includeInactive,
  ]);

  const loadStats = useCallback(async () => {
    try {
      const statsData = await apiService.getStats();
      setStats(statsData);
    } catch (err) {
      console.error("Load stats error:", err);
    }
  }, []);

  // Load initial data
  useEffect(() => {
    loadOpportunities();
    loadStats();
  }, [loadOpportunities, loadStats]);

  const handleSearchResults = (results: Opportunity[]) => {
    setOpportunities(results);
    setTotalItems(results.length);
    setPage(1); // Reset to first page when showing search results
  };

  const handleRefresh = () => {
    loadOpportunities();
    loadStats();
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "No deadline";
    try {
      return format(parseISO(dateString), "MMM dd, yyyy");
    } catch {
      return "Invalid date";
    }
  };

  const getDeadlineColor = (deadline?: string) => {
    if (!deadline) return "default";

    const deadlineDate = parseISO(deadline);
    const now = new Date();
    const oneWeek = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    const oneMonth = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);

    if (isBefore(deadlineDate, now)) return "error";
    if (isBefore(deadlineDate, oneWeek)) return "warning";
    if (isBefore(deadlineDate, oneMonth)) return "info";
    return "success";
  };

  const totalPages = Math.ceil(totalItems / itemsPerPage);

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Enhanced Research Opportunities
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          Advanced search, AI-powered discovery, and comprehensive data
          management
        </Typography>
      </Box>

      {/* Statistics Cards */}
      {stats && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Box>
                    <Typography color="text.secondary" gutterBottom>
                      Total Opportunities
                    </Typography>
                    <Typography variant="h4">
                      {stats.total_opportunities}
                    </Typography>
                  </Box>
                  <TrendingUpIcon color="primary" sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Box>
                    <Typography color="text.secondary" gutterBottom>
                      Active Opportunities
                    </Typography>
                    <Typography variant="h4" color="success.main">
                      {stats.active_opportunities}
                    </Typography>
                  </Box>
                  <AnalyticsIcon color="success" sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Box>
                    <Typography color="text.secondary" gutterBottom>
                      Recent (7 days)
                    </Typography>
                    <Typography variant="h4" color="info.main">
                      {stats.recent_opportunities}
                    </Typography>
                  </Box>
                  <AccessTimeIcon color="info" sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Box>
                    <Typography color="text.secondary" gutterBottom>
                      Upcoming Deadlines
                    </Typography>
                    <Typography variant="h4" color="warning.main">
                      {stats.upcoming_deadlines}
                    </Typography>
                  </Box>
                  <SchoolIcon color="warning" sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Enhanced Search Component */}
      <EnhancedSearch
        onResults={handleSearchResults}
        onLoading={setSearchLoading}
      />

      {/* Controls Section */}
      <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item xs={12} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Items per page</InputLabel>
              <Select
                value={itemsPerPage}
                label="Items per page"
                onChange={(e) => {
                  setItemsPerPage(Number(e.target.value));
                  setPage(1);
                }}
              >
                <MenuItem value={10}>10</MenuItem>
                <MenuItem value={20}>20</MenuItem>
                <MenuItem value={50}>50</MenuItem>
                <MenuItem value={100}>100</MenuItem>
                <MenuItem value={200}>200</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Sort by</InputLabel>
              <Select
                value={sortBy}
                label="Sort by"
                onChange={(e) => setSortBy(e.target.value)}
              >
                <MenuItem value="deadline">Deadline</MenuItem>
                <MenuItem value="created_at">Created Date</MenuItem>
                <MenuItem value="title">Title</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Order</InputLabel>
              <Select
                value={sortOrder}
                label="Order"
                onChange={(e) => setSortOrder(e.target.value)}
              >
                <MenuItem value="asc">Ascending</MenuItem>
                <MenuItem value="desc">Descending</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Category</InputLabel>
              <Select
                value={selectedCategory}
                label="Category"
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                <MenuItem value="">All Categories</MenuItem>
                {stats?.categories.map((cat) => (
                  <MenuItem key={cat.category} value={cat.category}>
                    <Badge badgeContent={cat.count} color="primary">
                      {cat.category}
                    </Badge>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={2}>
            <FormControlLabel
              control={
                <Switch
                  checked={includeInactive}
                  onChange={(e) => setIncludeInactive(e.target.checked)}
                  size="small"
                />
              }
              label="Include Inactive"
            />
          </Grid>

          <Grid item xs={12} md={1}>
            <Tooltip title="Refresh data">
              <Button
                variant="outlined"
                onClick={handleRefresh}
                disabled={loading || searchLoading}
                sx={{ minWidth: "auto", p: 1 }}
              >
                <RefreshIcon />
              </Button>
            </Tooltip>
          </Grid>
        </Grid>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Results Summary */}
      <Box
        sx={{
          mb: 2,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Typography variant="h6">
          {searchLoading
            ? "Searching..."
            : `Showing ${opportunities.length} of ${totalItems} opportunities`}
        </Typography>
        {totalPages > 1 && (
          <Typography variant="body2" color="text.secondary">
            Page {page} of {totalPages}
          </Typography>
        )}
      </Box>

      {/* Opportunities Grid */}
      {loading || searchLoading ? (
        <Grid container spacing={3}>
          {Array.from({ length: itemsPerPage }).map((_, index) => (
            <Grid item xs={12} md={6} lg={4} key={index}>
              <Card>
                <CardContent>
                  <Skeleton variant="text" width="80%" height={32} />
                  <Skeleton variant="text" width="60%" height={24} />
                  <Skeleton
                    variant="rectangular"
                    width="100%"
                    height={80}
                    sx={{ my: 2 }}
                  />
                  <Box sx={{ display: "flex", gap: 1 }}>
                    <Skeleton variant="rounded" width={60} height={24} />
                    <Skeleton variant="rounded" width={80} height={24} />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : opportunities.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="h6" gutterBottom>
            No opportunities found
          </Typography>
          <Typography color="text.secondary">
            Try adjusting your search criteria or refresh the data.
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {opportunities.map((opportunity) => (
            <Grid item xs={12} md={6} lg={4} key={opportunity.id}>
              <Card
                sx={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  opacity: opportunity.is_active ? 1 : 0.7,
                  borderLeft: opportunity.is_active
                    ? "4px solid #1976d2"
                    : "4px solid #757575",
                }}
              >
                <CardContent sx={{ flexGrow: 1 }}>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      mb: 2,
                    }}
                  >
                    <Typography
                      variant="h6"
                      component="h3"
                      sx={{ fontSize: "1.1rem", lineHeight: 1.3 }}
                    >
                      {opportunity.title}
                    </Typography>
                    {!opportunity.is_active && (
                      <Chip label="Inactive" size="small" color="default" />
                    )}
                  </Box>

                  {opportunity.description && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        mb: 2,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        display: "-webkit-box",
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: "vertical",
                      }}
                    >
                      {opportunity.description}
                    </Typography>
                  )}

                  <Box sx={{ mb: 2 }}>
                    {opportunity.category && (
                      <Chip
                        icon={<CategoryIcon />}
                        label={opportunity.category}
                        size="small"
                        variant="outlined"
                        sx={{ mr: 1, mb: 1 }}
                      />
                    )}

                    {opportunity.department && (
                      <Chip
                        icon={<SchoolIcon />}
                        label={opportunity.department}
                        size="small"
                        variant="outlined"
                        sx={{ mr: 1, mb: 1 }}
                      />
                    )}

                    {opportunity.location && (
                      <Chip
                        icon={<LocationIcon />}
                        label={opportunity.location}
                        size="small"
                        variant="outlined"
                        sx={{ mr: 1, mb: 1 }}
                      />
                    )}
                  </Box>

                  {opportunity.deadline && (
                    <Box
                      sx={{ display: "flex", alignItems: "center", mt: "auto" }}
                    >
                      <AccessTimeIcon sx={{ fontSize: 16, mr: 1 }} />
                      <Chip
                        label={`Deadline: ${formatDate(opportunity.deadline)}`}
                        size="small"
                        color={getDeadlineColor(opportunity.deadline)}
                        variant="filled"
                      />
                    </Box>
                  )}
                </CardContent>

                <Divider />

                <CardActions sx={{ p: 2 }}>
                  {opportunity.url && (
                    <Button
                      size="small"
                      endIcon={<OpenInNewIcon />}
                      href={opportunity.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      variant="contained"
                      fullWidth
                    >
                      View Details
                    </Button>
                  )}
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Pagination */}
      {totalPages > 1 && !searchLoading && (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_, newPage) => setPage(newPage)}
            color="primary"
            size="large"
            showFirstButton
            showLastButton
          />
        </Box>
      )}

      {/* Last Updated Info */}
      {stats && (
        <Box sx={{ mt: 4, textAlign: "center" }}>
          <Typography variant="caption" color="text.secondary">
            Last updated:{" "}
            {format(parseISO(stats.last_updated), "MMM dd, yyyy HH:mm")}
          </Typography>
        </Box>
      )}
    </Container>
  );
};

export default EnhancedResearchOpportunities;
