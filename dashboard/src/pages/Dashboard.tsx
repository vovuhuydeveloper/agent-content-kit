import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Paper, Chip, IconButton, Button,
  CircularProgress, LinearProgress, Skeleton, Grow,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import OpenInNewRoundedIcon from '@mui/icons-material/OpenInNewRounded';
import MovieCreationRoundedIcon from '@mui/icons-material/MovieCreationRounded';
import HourglassTopRoundedIcon from '@mui/icons-material/HourglassTopRounded';
import BoltRoundedIcon from '@mui/icons-material/BoltRounded';
import PhoneIphoneRoundedIcon from '@mui/icons-material/PhoneIphoneRounded';
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import RocketLaunchRoundedIcon from '@mui/icons-material/RocketLaunchRounded';
import CelebrationRoundedIcon from '@mui/icons-material/CelebrationRounded';
import ErrorRoundedIcon from '@mui/icons-material/ErrorRounded';
import BlockRoundedIcon from '@mui/icons-material/BlockRounded';
import { getJobs, deleteJob } from '../services/api';

interface Job {
  job_id: string;
  status: string;
  source_url: string;
  videos_count: number;
  published_count: number;
  created_at: string;
}

const STATUS_MAP: Record<string, { color: 'success' | 'warning' | 'error' | 'info' | 'default'; label: string; icon: React.ReactNode }> = {
  pending: { color: 'info', label: 'Queued', icon: <HourglassTopRoundedIcon sx={{ fontSize: 14 }} /> },
  running: { color: 'warning', label: 'Processing', icon: <BoltRoundedIcon sx={{ fontSize: 14 }} /> },
  awaiting_approval: { color: 'info', label: 'Review', icon: <PhoneIphoneRoundedIcon sx={{ fontSize: 14 }} /> },
  approved: { color: 'success', label: 'Approved', icon: <CheckCircleRoundedIcon sx={{ fontSize: 14 }} /> },
  publishing: { color: 'warning', label: 'Uploading', icon: <RocketLaunchRoundedIcon sx={{ fontSize: 14 }} /> },
  completed: { color: 'success', label: 'Done', icon: <CelebrationRoundedIcon sx={{ fontSize: 14 }} /> },
  failed: { color: 'error', label: 'Failed', icon: <ErrorRoundedIcon sx={{ fontSize: 14 }} /> },
  rejected: { color: 'default', label: 'Rejected', icon: <BlockRoundedIcon sx={{ fontSize: 14 }} /> },
};

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await getJobs();
      setJobs(data.jobs || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (id: string) => {
    if (confirm('Delete this job?')) {
      await deleteJob(id);
      fetchJobs();
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 0.5 }}>Dashboard</Typography>
          <Typography variant="body2" color="text.secondary">
            {total} content {total === 1 ? 'job' : 'jobs'} total
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <IconButton
            onClick={fetchJobs}
            size="small"
            sx={{
              color: 'text.secondary',
              transition: 'all 0.3s ease',
              '&:hover': { color: 'primary.main', transform: 'rotate(180deg)' },
            }}
          >
            <RefreshRoundedIcon fontSize="small" />
          </IconButton>
          <Button variant="contained" startIcon={<AddRoundedIcon />} onClick={() => navigate('/setup')} size="small">
            New job
          </Button>
        </Box>
      </Box>

      {/* Content */}
      {loading && jobs.length === 0 ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} variant="rounded" height={72} sx={{ borderRadius: 3, bgcolor: alpha('#6366F1', 0.04) }} />
          ))}
        </Box>
      ) : jobs.length === 0 ? (
        <Paper sx={{
          p: 8, textAlign: 'center', borderRadius: 4,
          border: '2px dashed rgba(15, 23, 42, 0.08)',
          bgcolor: 'transparent', boxShadow: 'none',
        }}>
          <MovieCreationRoundedIcon sx={{ fontSize: 56, color: '#CBD5E1', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" sx={{ mb: 0.5 }}>
            No content jobs yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Create your first AI video pipeline
          </Typography>
          <Button variant="contained" startIcon={<AddRoundedIcon />} onClick={() => navigate('/setup')}>
            Create first video
          </Button>
        </Paper>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {jobs.map((job, index) => {
            const st = STATUS_MAP[job.status] || { color: 'default' as const, label: job.status, icon: null };
            const isRunning = ['running', 'pending', 'publishing'].includes(job.status);

            return (
              <Grow in key={job.job_id} timeout={300 + index * 80}>
                <Paper
                  sx={{
                    p: 2, borderRadius: 3, cursor: 'pointer',
                    transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&:hover': {
                      borderColor: alpha('#6366F1', 0.15),
                      boxShadow: `0 8px 24px ${alpha('#6366F1', 0.08)}`,
                      transform: 'translateY(-2px)',
                    },
                  }}
                  onClick={() => navigate(`/jobs/${job.job_id}`)}
                >
                  {isRunning && (
                    <LinearProgress sx={{
                      mb: 1.5, borderRadius: 1, height: 3,
                      bgcolor: alpha('#6366F1', 0.06),
                      '& .MuiLinearProgress-bar': {
                        bgcolor: '#6366F1',
                        animation: 'pulse-bar 2s ease-in-out infinite',
                      },
                    }} />
                  )}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box sx={{
                      width: 40, height: 40, borderRadius: '10px',
                      bgcolor: alpha('#6366F1', 0.06), color: '#818CF8',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0, transition: 'all 0.2s ease',
                    }}>
                      <MovieCreationRoundedIcon sx={{ fontSize: 20 }} />
                    </Box>
                    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                      <Typography variant="subtitle1" fontWeight={600} noWrap>
                        {job.source_url.replace(/^https?:\/\//, '').slice(0, 55)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {job.created_at ? new Date(job.created_at).toLocaleString('vi') : ''}
                      </Typography>
                    </Box>
                    <Chip
                      icon={st.icon as React.ReactElement}
                      label={st.label}
                      color={st.color}
                      size="small"
                      variant="outlined"
                    />
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 55, textAlign: 'center', fontWeight: 500 }}>
                      {job.videos_count || 0} vid
                    </Typography>
                    <IconButton
                      size="small"
                      onClick={(e) => { e.stopPropagation(); navigate(`/jobs/${job.job_id}`); }}
                      sx={{ color: 'text.secondary', transition: 'all 0.2s', '&:hover': { color: 'primary.main', transform: 'scale(1.1)' } }}
                    >
                      <OpenInNewRoundedIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={(e) => { e.stopPropagation(); handleDelete(job.job_id); }}
                      sx={{ color: 'text.secondary', transition: 'all 0.2s', '&:hover': { color: 'error.main', transform: 'scale(1.1)' } }}
                    >
                      <DeleteOutlineRoundedIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </Paper>
              </Grow>
            );
          })}
        </Box>
      )}
    </Box>
  );
}
