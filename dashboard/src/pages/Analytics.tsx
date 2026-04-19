import { useState, useEffect } from 'react';
import {
  Box, Typography, Paper, CircularProgress,
  IconButton, Select, MenuItem, FormControl, InputLabel, Grow,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import VisibilityRoundedIcon from '@mui/icons-material/VisibilityRounded';
import FavoriteRoundedIcon from '@mui/icons-material/FavoriteRounded';
import ChatBubbleOutlineRoundedIcon from '@mui/icons-material/ChatBubbleOutlineRounded';
import TrendingUpRoundedIcon from '@mui/icons-material/TrendingUpRounded';
import EmojiEventsRoundedIcon from '@mui/icons-material/EmojiEventsRounded';
import ScienceRoundedIcon from '@mui/icons-material/ScienceRounded';
import api from '../services/api';

interface OverviewData {
  period_days: number;
  total_videos: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  avg_engagement_rate: number;
  completed_jobs: number;
  platforms: { platform: string; video_count: number; total_views: number; total_likes: number; avg_engagement: number }[];
}

interface TopVideo { id: string; platform: string; post_url: string; views: number; likes: number; engagement_rate: number; variant: string; }
interface ABResult { variant: string; video_count: number; total_views: number; total_likes: number; avg_engagement: number; }

const PLATFORM_COLORS: Record<string, string> = { tiktok: '#25F4EE', youtube: '#FF0000', facebook: '#1877F2', instagram: '#E4405F' };

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

interface MetricCardProps { icon: React.ReactNode; label: string; value: string; color: string; sub?: string; delay: number; }

function MetricCard({ icon, label, value, color, sub, delay }: MetricCardProps) {
  return (
    <Grow in timeout={400 + delay}>
      <Paper sx={{
        p: 2.5, borderRadius: 3,
        transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        '&:hover': { transform: 'translateY(-3px)', boxShadow: `0 8px 24px ${alpha(color, 0.12)}`, borderColor: alpha(color, 0.15) },
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
          <Box sx={{
            width: 36, height: 36, borderRadius: '9px',
            bgcolor: alpha(color, 0.08), color: color,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'transform 0.3s ease',
          }}>
            {icon}
          </Box>
          <Typography variant="body2" color="text.secondary" fontWeight={500}>{label}</Typography>
        </Box>
        <Typography variant="h4" fontWeight={700} sx={{ color, lineHeight: 1 }}>{value}</Typography>
        {sub && <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>{sub}</Typography>}
      </Paper>
    </Grow>
  );
}

export default function Analytics() {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [topVideos, setTopVideos] = useState<TopVideo[]>([]);
  const [abResults, setAbResults] = useState<ABResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(30);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [overviewRes, topRes, abRes] = await Promise.all([
        api.get(`/analytics/overview?days=${period}`),
        api.get('/analytics/top-videos?limit=5'),
        api.get('/analytics/ab-results'),
      ]);
      setOverview(overviewRes.data);
      setTopVideos(topRes.data.videos || []);
      setAbResults(abRes.data.results || []);
    } catch (err) { console.error('Failed to load analytics:', err); }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, [period]);

  if (loading) {
    return <Box sx={{ textAlign: 'center', py: 10 }}><CircularProgress size={32} sx={{ color: '#6366F1' }} /></Box>;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 0.5 }}>Insights</Typography>
          <Typography variant="body2" color="text.secondary">Video performance across platforms</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel>Period</InputLabel>
            <Select value={period} onChange={(e) => setPeriod(e.target.value as number)} label="Period">
              <MenuItem value={7}>7 days</MenuItem>
              <MenuItem value={30}>30 days</MenuItem>
              <MenuItem value={90}>90 days</MenuItem>
            </Select>
          </FormControl>
          <IconButton onClick={fetchData} size="small" sx={{ color: 'text.secondary', transition: 'all 0.3s', '&:hover': { transform: 'rotate(180deg)', color: 'primary.main' } }}>
            <RefreshRoundedIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>

      {overview && (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 2, mb: 4 }}>
          <MetricCard icon={<VisibilityRoundedIcon sx={{ fontSize: 20 }} />} label="Views" value={formatNumber(overview.total_views)} color="#3B82F6" sub={`${overview.total_videos} videos`} delay={0} />
          <MetricCard icon={<FavoriteRoundedIcon sx={{ fontSize: 20 }} />} label="Likes" value={formatNumber(overview.total_likes)} color="#EF4444" delay={100} />
          <MetricCard icon={<ChatBubbleOutlineRoundedIcon sx={{ fontSize: 20 }} />} label="Comments" value={formatNumber(overview.total_comments)} color="#F59E0B" delay={200} />
          <MetricCard icon={<TrendingUpRoundedIcon sx={{ fontSize: 20 }} />} label="Engagement" value={`${overview.avg_engagement_rate}%`} color="#10B981" sub={`${overview.completed_jobs} jobs completed`} delay={300} />
        </Box>
      )}

      {/* Platform Breakdown */}
      {overview && overview.platforms.length > 0 && (
        <Grow in timeout={500}>
          <Paper sx={{ p: 3, mb: 3, borderRadius: 3, transition: 'all 0.25s ease', '&:hover': { boxShadow: '0 8px 24px rgba(15,23,42,0.06)' } }}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>By Platform</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {overview.platforms.map((p) => {
                const maxViews = Math.max(...overview.platforms.map((x) => x.total_views), 1);
                const color = PLATFORM_COLORS[p.platform] || '#6366F1';
                return (
                  <Box key={p.platform}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="body2" fontWeight={600} sx={{ textTransform: 'capitalize' }}>{p.platform}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatNumber(p.total_views)} views · {formatNumber(p.total_likes)} likes · {p.avg_engagement}% ER
                      </Typography>
                    </Box>
                    <Box sx={{ height: 6, borderRadius: 3, bgcolor: alpha(color, 0.08), overflow: 'hidden' }}>
                      <Box sx={{
                        height: '100%', borderRadius: 3, width: `${(p.total_views / maxViews) * 100}%`,
                        bgcolor: color, transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                      }} />
                    </Box>
                  </Box>
                );
              })}
            </Box>
          </Paper>
        </Grow>
      )}

      {/* Top Videos */}
      {topVideos.length > 0 && (
        <Grow in timeout={600}>
          <Paper sx={{ p: 3, mb: 3, borderRadius: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <EmojiEventsRoundedIcon sx={{ fontSize: 20, color: '#F59E0B' }} />
              <Typography variant="subtitle2" color="text.secondary">Top Performing</Typography>
            </Box>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {topVideos.map((v, i) => (
                <Box key={v.id} sx={{
                  display: 'flex', alignItems: 'center', gap: 2, py: 1,
                  borderBottom: i < topVideos.length - 1 ? '1px solid rgba(15,23,42,0.04)' : 'none',
                  transition: 'background 0.2s', '&:hover': { bgcolor: alpha('#6366F1', 0.02), borderRadius: 2 },
                }}>
                  <Typography variant="body2" fontWeight={700} sx={{ width: 24, textAlign: 'center', color: i < 3 ? '#F59E0B' : '#94A3B8' }}>
                    {i + 1}
                  </Typography>
                  <Box sx={{
                    px: 1, py: 0.25, borderRadius: 1, fontSize: '0.7rem', fontWeight: 600,
                    bgcolor: alpha(PLATFORM_COLORS[v.platform] || '#6366F1', 0.08),
                    color: PLATFORM_COLORS[v.platform] || '#6366F1', textTransform: 'capitalize',
                  }}>{v.platform}</Box>
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {formatNumber(v.views)} views · {formatNumber(v.likes)} likes · {v.engagement_rate}% ER
                    </Typography>
                  </Box>
                  {v.variant && (
                    <Box sx={{ px: 1, py: 0.25, borderRadius: 1, fontSize: '0.7rem', border: '1px solid', borderColor: alpha('#6366F1', 0.15), color: '#6366F1' }}>
                      Variant {v.variant}
                    </Box>
                  )}
                </Box>
              ))}
            </Box>
          </Paper>
        </Grow>
      )}

      {/* A/B Results */}
      {abResults.length > 0 && (
        <Grow in timeout={700}>
          <Paper sx={{ p: 3, borderRadius: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <ScienceRoundedIcon sx={{ fontSize: 20, color: '#3B82F6' }} />
              <Typography variant="subtitle2" color="text.secondary">A/B Test Results</Typography>
            </Box>
            <Box sx={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(abResults.length, 3)}, 1fr)`, gap: 2 }}>
              {abResults.map((r, i) => (
                <Paper key={r.variant} elevation={0} sx={{
                  p: 2.5, textAlign: 'center', borderRadius: 3,
                  bgcolor: i === 0 ? alpha('#10B981', 0.04) : alpha('#94A3B8', 0.03),
                  border: `1px solid ${i === 0 ? alpha('#10B981', 0.12) : 'rgba(15,23,42,0.04)'}`,
                  transition: 'all 0.25s', '&:hover': { transform: 'translateY(-2px)' },
                }}>
                  <Typography variant="body2" fontWeight={600} color="text.secondary">Variant {r.variant}</Typography>
                  <Typography variant="h4" fontWeight={700} sx={{ my: 1, color: i === 0 ? '#10B981' : '#0F172A' }}>
                    {r.avg_engagement}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {r.video_count} videos · {formatNumber(r.total_views)} views
                  </Typography>
                </Paper>
              ))}
            </Box>
          </Paper>
        </Grow>
      )}

      {/* Empty State */}
      {overview && overview.total_videos === 0 && (
        <Paper sx={{ p: 8, textAlign: 'center', borderRadius: 4, border: '2px dashed rgba(15,23,42,0.08)', bgcolor: 'transparent', boxShadow: 'none' }}>
          <TrendingUpRoundedIcon sx={{ fontSize: 56, color: '#CBD5E1', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" sx={{ mb: 0.5 }}>No analytics data yet</Typography>
          <Typography variant="body2" color="text.secondary">Publish videos to start tracking performance</Typography>
        </Paper>
      )}
    </Box>
  );
}
