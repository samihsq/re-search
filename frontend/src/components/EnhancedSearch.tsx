import React, { useState } from "react";
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Chip,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Tabs,
  Tab,
  Card,
  CardContent,
  Grid,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import {
  Search as SearchIcon,
  AutoAwesome as AIIcon,
  ViewList as AllPagesIcon,
  CloudDownload as ScrapingIcon,
  ExpandMore as ExpandMoreIcon,
  Speed as SpeedIcon,
  Psychology as PsychologyIcon,
  Storage as DatabaseIcon,
} from "@mui/icons-material";
import {
  apiService,
  Opportunity,
  LLMSearchResponse,
  AllPagesSearchResponse,
  ScrapingResponse,
} from "../services/api";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`search-tabpanel-${index}`}
      aria-labelledby={`search-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

interface EnhancedSearchProps {
  onResults: (opportunities: Opportunity[]) => void;
  onLoading: (loading: boolean) => void;
}

const EnhancedSearch: React.FC<EnhancedSearchProps> = ({
  onResults,
  onLoading,
}) => {
  // State management
  const [activeTab, setActiveTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [category, setCategory] = useState("");
  const [deadlineAfter, setDeadlineAfter] = useState("");
  const [deadlineBefore, setDeadlineBefore] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [limit, setLimit] = useState(50);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<{
    normal?: Opportunity[];
    llm?: LLMSearchResponse;
    allPages?: AllPagesSearchResponse;
  }>({});
  const [error, setError] = useState<string | null>(null);
  const [scrapingStatus, setScrapingStatus] = useState<{
    isRunning: boolean;
    results?: ScrapingResponse;
  }>({ isRunning: false });

  // Available categories (you might want to fetch these from the API)
  const categories = [
    "Research",
    "Internship",
    "Fellowship",
    "Graduate",
    "Undergraduate",
    "Machine Learning",
    "AI",
    "Biology",
    "Chemistry",
    "Physics",
    "Engineering",
    "Computer Science",
  ];

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
    setError(null);
  };

  const resetSearch = () => {
    setSearchResults({});
    setError(null);
    onResults([]);
  };

  // Enhanced search (normal search with enhanced pagination)
  const handleEnhancedSearch = async () => {
    setIsSearching(true);
    setError(null);
    onLoading(true);

    try {
      const results = await apiService.getOpportunities({
        search: searchQuery || undefined,
        category: category || undefined,
        deadline_after: deadlineAfter || undefined,
        deadline_before: deadlineBefore || undefined,
        include_inactive: includeInactive,
        limit: Math.min(limit, 10000), // Enhanced limit
        skip: 0,
      });

      setSearchResults((prev) => ({ ...prev, normal: results.opportunities }));
      onResults(results.opportunities);
    } catch (err) {
      setError("Enhanced search failed. Please try again.");
      console.error("Enhanced search error:", err);
    } finally {
      setIsSearching(false);
      onLoading(false);
    }
  };

  // LLM-powered search (RAG)
  const handleLLMSearch = async () => {
    if (!searchQuery.trim()) {
      setError("Please enter a search query for AI search.");
      return;
    }

    setIsSearching(true);
    setError(null);
    onLoading(true);

    try {
      const results = await apiService.llmSearch({
        query: searchQuery,
        limit: Math.min(limit, 1000),
        include_inactive: includeInactive,
      });

      setSearchResults((prev) => ({ ...prev, llm: results }));
      onResults(results.opportunities);
    } catch (err) {
      setError("AI search failed. Please try again.");
      console.error("LLM search error:", err);
    } finally {
      setIsSearching(false);
      onLoading(false);
    }
  };

  // All-pages search
  const handleAllPagesSearch = async () => {
    setIsSearching(true);
    setError(null);
    onLoading(true);

    try {
      const results = await apiService.searchAllPages({
        search_term: searchQuery || undefined,
        category: category || undefined,
        deadline_after: deadlineAfter || undefined,
        deadline_before: deadlineBefore || undefined,
        include_inactive: includeInactive,
        limit: Math.min(limit, 10000),
      });

      setSearchResults((prev) => ({ ...prev, allPages: results }));
      onResults(results.opportunities);
    } catch (err) {
      setError("All-pages search failed. Please try again.");
      console.error("All-pages search error:", err);
    } finally {
      setIsSearching(false);
      onLoading(false);
    }
  };

  // Scraping functions
  const handleBasicScraping = async () => {
    setScrapingStatus({ isRunning: true });
    setError(null);

    try {
      const results = await apiService.startScraping();
      setScrapingStatus({ isRunning: false, results });
    } catch (err) {
      setError("Basic scraping failed. Please try again.");
      setScrapingStatus({ isRunning: false });
      console.error("Scraping error:", err);
    }
  };

  const handleEnhancedScraping = async () => {
    setScrapingStatus({ isRunning: true });
    setError(null);

    try {
      const results = await apiService.startEnhancedScraping();
      setScrapingStatus({ isRunning: false, results });
    } catch (err) {
      setError("Enhanced scraping failed. Please try again.");
      setScrapingStatus({ isRunning: false });
      console.error("Enhanced scraping error:", err);
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
      <Typography
        variant="h5"
        gutterBottom
        sx={{ display: "flex", alignItems: "center", gap: 1 }}
      >
        <SearchIcon />
        Enhanced Search & Data Management
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          aria-label="search tabs"
        >
          <Tab
            icon={<SpeedIcon />}
            label="Enhanced Search"
            iconPosition="start"
            sx={{ minHeight: 48 }}
          />
          <Tab
            icon={<PsychologyIcon />}
            label="AI Search (RAG)"
            iconPosition="start"
            sx={{ minHeight: 48 }}
          />
          <Tab
            icon={<DatabaseIcon />}
            label="All-Pages Search"
            iconPosition="start"
            sx={{ minHeight: 48 }}
          />
          <Tab
            icon={<ScrapingIcon />}
            label="Data Scraping"
            iconPosition="start"
            sx={{ minHeight: 48 }}
          />
        </Tabs>
      </Box>

      {/* Enhanced Search Tab */}
      <TabPanel value={activeTab} index={0}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Alert severity="info" sx={{ mb: 2 }}>
              <strong>Enhanced Search:</strong> Traditional search with improved
              pagination (up to 10,000 results) and advanced filtering options.
            </Alert>
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Search Query"
              placeholder="Enter keywords, titles, descriptions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleEnhancedSearch()}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Category</InputLabel>
              <Select
                value={category}
                label="Category"
                onChange={(e) => setCategory(e.target.value)}
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

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="date"
              label="Deadline After"
              value={deadlineAfter}
              onChange={(e) => setDeadlineAfter(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="date"
              label="Deadline Before"
              value={deadlineBefore}
              onChange={(e) => setDeadlineBefore(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="number"
              label="Result Limit"
              value={limit}
              onChange={(e) =>
                setLimit(
                  Math.min(10000, Math.max(1, parseInt(e.target.value) || 50))
                )
              }
              inputProps={{ min: 1, max: 10000 }}
              helperText="Max: 10,000 results"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControlLabel
              control={
                <Switch
                  checked={includeInactive}
                  onChange={(e) => setIncludeInactive(e.target.checked)}
                />
              }
              label="Include Inactive Opportunities"
            />
          </Grid>

          <Grid item xs={12}>
            <Box sx={{ display: "flex", gap: 2 }}>
              <Button
                variant="contained"
                startIcon={
                  isSearching ? <CircularProgress size={20} /> : <SearchIcon />
                }
                onClick={handleEnhancedSearch}
                disabled={isSearching}
                size="large"
              >
                {isSearching ? "Searching..." : "Enhanced Search"}
              </Button>
              <Button variant="outlined" onClick={resetSearch}>
                Clear Results
              </Button>
            </Box>
          </Grid>
        </Grid>
      </TabPanel>

      {/* LLM Search Tab */}
      <TabPanel value={activeTab} index={1}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Alert severity="info" sx={{ mb: 2 }}>
              <strong>AI-Powered Search (RAG):</strong> Natural language search
              using AI to understand context and rank results by relevance. Ask
              questions like "machine learning internships for undergraduates"
              or "biology research with summer deadlines".
            </Alert>
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              multiline
              rows={3}
              label="Natural Language Query"
              placeholder="e.g., 'Find machine learning research opportunities for undergraduate students' or 'What internships are available in computer science?'"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="number"
              label="Result Limit"
              value={limit}
              onChange={(e) =>
                setLimit(
                  Math.min(1000, Math.max(1, parseInt(e.target.value) || 50))
                )
              }
              inputProps={{ min: 1, max: 1000 }}
              helperText="Max: 1,000 results for AI analysis"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControlLabel
              control={
                <Switch
                  checked={includeInactive}
                  onChange={(e) => setIncludeInactive(e.target.checked)}
                />
              }
              label="Include Inactive Opportunities"
            />
          </Grid>

          <Grid item xs={12}>
            <Box sx={{ display: "flex", gap: 2 }}>
              <Button
                variant="contained"
                startIcon={
                  isSearching ? <CircularProgress size={20} /> : <AIIcon />
                }
                onClick={handleLLMSearch}
                disabled={isSearching || !searchQuery.trim()}
                size="large"
                color="secondary"
              >
                {isSearching ? "AI Analyzing..." : "AI Search"}
              </Button>
              <Button variant="outlined" onClick={resetSearch}>
                Clear Results
              </Button>
            </Box>
          </Grid>

          {searchResults.llm && (
            <Grid item xs={12}>
              <Card sx={{ mt: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    AI Analysis Results
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    <strong>Processing Time:</strong>{" "}
                    {searchResults.llm.processing_time.toFixed(2)}s
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>AI Explanation:</strong>{" "}
                    {searchResults.llm.ai_explanation}
                  </Typography>
                  <Chip
                    label={`${searchResults.llm.total_found} results found`}
                    color="primary"
                    size="small"
                  />
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      </TabPanel>

      {/* All-Pages Search Tab */}
      <TabPanel value={activeTab} index={2}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Alert severity="info" sx={{ mb: 2 }}>
              <strong>All-Pages Search:</strong> Search across the entire
              database without pagination limits. Perfect for comprehensive
              analysis and finding all matching opportunities.
            </Alert>
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Search Term"
              placeholder="Search across all opportunities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleAllPagesSearch()}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Category</InputLabel>
              <Select
                value={category}
                label="Category"
                onChange={(e) => setCategory(e.target.value)}
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

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="date"
              label="Deadline After"
              value={deadlineAfter}
              onChange={(e) => setDeadlineAfter(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="date"
              label="Deadline Before"
              value={deadlineBefore}
              onChange={(e) => setDeadlineBefore(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="number"
              label="Result Limit"
              value={limit}
              onChange={(e) =>
                setLimit(
                  Math.min(10000, Math.max(1, parseInt(e.target.value) || 1000))
                )
              }
              inputProps={{ min: 1, max: 10000 }}
              helperText="Max: 10,000 results"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControlLabel
              control={
                <Switch
                  checked={includeInactive}
                  onChange={(e) => setIncludeInactive(e.target.checked)}
                />
              }
              label="Include Inactive Opportunities"
            />
          </Grid>

          <Grid item xs={12}>
            <Box sx={{ display: "flex", gap: 2 }}>
              <Button
                variant="contained"
                startIcon={
                  isSearching ? (
                    <CircularProgress size={20} />
                  ) : (
                    <AllPagesIcon />
                  )
                }
                onClick={handleAllPagesSearch}
                disabled={isSearching}
                size="large"
                color="success"
              >
                {isSearching ? "Searching All Pages..." : "Search All Pages"}
              </Button>
              <Button variant="outlined" onClick={resetSearch}>
                Clear Results
              </Button>
            </Box>
          </Grid>

          {searchResults.allPages && (
            <Grid item xs={12}>
              <Card sx={{ mt: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    All-Pages Search Results
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    <strong>Processing Time:</strong>{" "}
                    {searchResults.allPages.processing_time.toFixed(2)}s
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>Search Parameters:</strong>{" "}
                    {JSON.stringify(
                      searchResults.allPages.search_params,
                      null,
                      2
                    )}
                  </Typography>
                  <Chip
                    label={`${searchResults.allPages.total_found} total results found`}
                    color="success"
                    size="small"
                  />
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      </TabPanel>

      {/* Scraping Tab */}
      <TabPanel value={activeTab} index={3}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Alert severity="warning" sx={{ mb: 2 }}>
              <strong>Data Scraping:</strong> Collect new research opportunities
              from configured sources. Enhanced scraping uses AI to better parse
              and understand content.
            </Alert>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Basic Scraping
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Standard web scraping from configured research opportunity
                  sources.
                </Typography>
                <Button
                  variant="contained"
                  startIcon={
                    scrapingStatus.isRunning ? (
                      <CircularProgress size={20} />
                    ) : (
                      <ScrapingIcon />
                    )
                  }
                  onClick={handleBasicScraping}
                  disabled={scrapingStatus.isRunning}
                  fullWidth
                >
                  {scrapingStatus.isRunning
                    ? "Scraping..."
                    : "Start Basic Scraping"}
                </Button>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Enhanced Scraping (AI)
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  AI-powered scraping with intelligent content parsing and
                  understanding.
                </Typography>
                <Button
                  variant="contained"
                  startIcon={
                    scrapingStatus.isRunning ? (
                      <CircularProgress size={20} />
                    ) : (
                      <AIIcon />
                    )
                  }
                  onClick={handleEnhancedScraping}
                  disabled={scrapingStatus.isRunning}
                  fullWidth
                  color="secondary"
                >
                  {scrapingStatus.isRunning
                    ? "AI Scraping..."
                    : "Start Enhanced Scraping"}
                </Button>
              </CardContent>
            </Card>
          </Grid>

          {scrapingStatus.isRunning && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Scraping in Progress...
                  </Typography>
                  <LinearProgress sx={{ mt: 1 }} />
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 1 }}
                  >
                    This may take several minutes depending on the number of
                    sources.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          )}

          {scrapingStatus.results && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Scraping Results
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="body2" color="text.secondary">
                        Total Scraped
                      </Typography>
                      <Typography variant="h6">
                        {scrapingStatus.results.total_scraped}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="body2" color="text.secondary">
                        New Opportunities
                      </Typography>
                      <Typography variant="h6" color="success.main">
                        {scrapingStatus.results.new_opportunities}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="body2" color="text.secondary">
                        Updated
                      </Typography>
                      <Typography variant="h6" color="info.main">
                        {scrapingStatus.results.updated_opportunities}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="body2" color="text.secondary">
                        Processing Time
                      </Typography>
                      <Typography variant="h6">
                        {scrapingStatus.results.processing_time.toFixed(1)}s
                      </Typography>
                    </Grid>
                  </Grid>

                  {scrapingStatus.results.errors.length > 0 && (
                    <Accordion sx={{ mt: 2 }}>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography color="error">
                          {scrapingStatus.results.errors.length} Errors Occurred
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        {scrapingStatus.results.errors.map((error, index) => (
                          <Typography
                            key={index}
                            variant="body2"
                            color="error"
                            paragraph
                          >
                            {error}
                          </Typography>
                        ))}
                      </AccordionDetails>
                    </Accordion>
                  )}

                  <Typography variant="body2" sx={{ mt: 2 }}>
                    {scrapingStatus.results.message}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      </TabPanel>
    </Paper>
  );
};

export default EnhancedSearch;
