import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Paper, Chip, Button, CircularProgress,
  Divider, Alert, LinearProgress, IconButton, Grow, Collapse,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded';
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import CancelRoundedIcon from '@mui/icons-material/CancelRounded';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import FolderRoundedIcon from '@mui/icons-material/FolderRounded';
import VideoFileRoundedIcon from '@mui/icons-material/VideoFileRounded';
import AudioFileRoundedIcon from '@mui/icons-material/AudioFileRounded';
import ImageRoundedIcon from '@mui/icons-material/ImageRounded';
import DescriptionRoundedIcon from '@mui/icons-material/DescriptionRounded';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import { getJob, approveJob, rejectJob, getJobFiles } from '../services/api';

interface JobData {
  job_id: string;
  status: string;
  source_url: string;
  language: string;
  platforms: string[];
  progress: number;
  current_agent: string;
  scripts_count: number;
  videos_count: number;
  published_count: number;
  elapsed_seconds: number;
  error: string | null;
  pipeline_result: any;
  created_at: string;
  started_at: string;
  completed_at: string;
}

interface OutputFile {
  name: string;
  path: string;
  type: string;
  size: number;
  url: string;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const FILE_ICONS: Record<string, React.ReactNode> = {
  video: <VideoFileRoundedIcon sx={{ color: '#6366F1' }} />,
  audio: <AudioFileRoundedIcon sx={{ color: '#F59E0B' }} />,
  image: <ImageRoundedIcon sx={{ color: '#10B981' }} />,
  data: <DescriptionRoundedIcon sx={{ color: '#94A3B8' }} />,
  other: <DescriptionRoundedIcon sx={{ color: '#94A3B8' }} />,
};

export default function JobDetail() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobData | null>(null);
  const [files, setFiles] = useState<OutputFile[]>([]);
  const [jobDir, setJobDir] = useState('');
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const navigate = useNavigate();

  const fetchJob = async () => {
    if (!jobId) return;
    try {
      const data = await getJob(jobId);
      setJob(data);
    } catch (err) {
      console.error('Failed to load job:', err);
    }
    setLoading(false);
  };

  const fetchFiles = async () => {
    if (!jobId) return;
    try {
      const res = await getJobFiles(jobId);
      setFiles(res.files || []);
      setJobDir(res.job_dir || '');
    } catch { /* ignore */ }
  };

  useEffect(() => {
    fetchJob();
    fetchFiles();
    const interval = setInterval(() => { fetchJob(); fetchFiles(); }, 5000);
    return () => clearInterval(interval);
  }, [jobId]);

  const handleApprove = async () => {
    if (!jobId) return;
    setActing(true);
    try { await approveJob(jobId); fetchJob(); }
    catch (err) { console.error('Approve failed:', err); }
    setActing(false);
  };

  const handleReject = async () => {
    if (!jobId) return;
    setActing(true);
    try { await rejectJob(jobId); fetchJob(); }
    catch (err) { console.error('Reject failed:', err); }
    setActing(false);
  };

  if (loading) {
    return <Box sx={{ textAlign: 'center', py: 10 }}><CircularProgress size={32} sx={{ color: '#6366F1' }} /></Box>;
  }

  if (!job) {
    return <Alert severity="error" sx={{ borderRadius: 3 }}>Job not found</Alert>;
  }

  const isRunning = ['running', 'pending', 'publishing'].includes(job.status);
  const canApprove = job.status === 'awaiting_approval';

  const videos = files.filter(f => f.type === 'video');
  const thumbnails = files.filter(f => f.type === 'image' && !f.path.includes('temp_render'));
  const audioFiles = files.filter(f => f.type === 'audio');

  return (
    <Box>
      <Button
        startIcon={<ArrowBackRoundedIcon />}
        onClick={() => navigate('/dashboard')}
        sx={{ mb: 3, color: 'text.secondary', '&:hover': { color: 'text.primary' } }}
        size="small"
      >
        Back to Dashboard
      </Button>

      <Grow in timeout={300}>
      <Paper sx={{ p: 3, mb: 3, borderRadius: 3, transition: 'all 0.25s ease', '&:hover': { boxShadow: '0 8px 24px rgba(15,23,42,0.06)' } }}>
        {isRunning && (
          <LinearProgress sx={{
            mb: 2, borderRadius: 1, height: 3,
            bgcolor: alpha('#6366F1', 0.08),
            '& .MuiLinearProgress-bar': { bgcolor: '#6366F1' },
          }} />
        )}

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <Typography variant="h5" sx={{ flexGrow: 1 }}>Job Details</Typography>
          <IconButton onClick={() => { fetchJob(); fetchFiles(); }} size="small" sx={{ color: 'text.secondary' }}>
            <RefreshRoundedIcon fontSize="small" />
          </IconButton>
          <Chip
            label={job.status.replace('_', ' ').toUpperCase()}
            size="small"
            color={
              job.status === 'completed' ? 'success' :
              job.status === 'failed' ? 'error' :
              job.status === 'awaiting_approval' ? 'info' :
              'warning'
            }
            variant="outlined"
          />
        </Box>

        <Divider sx={{ mb: 2, borderColor: 'rgba(148,163,184,0.06)' }} />

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <InfoRow label="Source" value={job.source_url.replace(/^https?:\/\//, '').slice(0, 50)} />
          <InfoRow label="Language" value={job.language === 'vi' ? 'Vietnamese' : 'English'} />
          <InfoRow label="Platforms" value={job.platforms?.join(', ') || 'N/A'} />
          <InfoRow label="Scripts" value={String(job.scripts_count || 0)} />
          <InfoRow label="Videos" value={String(job.videos_count || 0)} />
          <InfoRow label="Published" value={String(job.published_count || 0)} />
          <InfoRow label="Elapsed" value={job.elapsed_seconds ? `${job.elapsed_seconds.toFixed(0)}s` : '—'} />
          <InfoRow label="Created" value={job.created_at ? new Date(job.created_at).toLocaleString() : '—'} />
        </Box>

        {job.error && (
          <Alert severity="error" sx={{ mt: 2, borderRadius: 2 }}>{job.error}</Alert>
        )}
      </Paper>
      </Grow>

      {/* Video Preview */}
      {videos.length > 0 && (
        <Grow in timeout={400}>
        <Paper sx={{ p: 3, mb: 3, borderRadius: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <VideoFileRoundedIcon sx={{ color: '#6366F1' }} /> Video Preview
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: videos.length > 1 ? '1fr 1fr' : '1fr', gap: 2 }}>
            {videos.map((v) => (
              <Box key={v.path} sx={{
                borderRadius: 2, overflow: 'hidden',
                border: `1px solid ${alpha('#94A3B8', 0.1)}`,
              }}>
                <video
                  controls
                  style={{ width: '100%', maxHeight: 400, background: '#000' }}
                  src={v.url}
                />
                <Box sx={{ p: 1.5, display: 'flex', alignItems: 'center', gap: 1, bgcolor: alpha('#94A3B8', 0.04) }}>
                  <Typography variant="caption" sx={{ flexGrow: 1 }}>{v.name}</Typography>
                  <Chip label={formatSize(v.size)} size="small" variant="outlined" />
                  <IconButton size="small" href={v.url} download>
                    <DownloadRoundedIcon fontSize="small" />
                  </IconButton>
                </Box>
              </Box>
            ))}
          </Box>
        </Paper>
        </Grow>
      )}

      {/* Thumbnails */}
      {thumbnails.length > 0 && (
        <Grow in timeout={500}>
        <Paper sx={{ p: 3, mb: 3, borderRadius: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <ImageRoundedIcon sx={{ color: '#10B981' }} /> Thumbnails
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {thumbnails.map((img) => (
              <Box key={img.path} sx={{
                borderRadius: 2, overflow: 'hidden', width: 200,
                border: `1px solid ${alpha('#94A3B8', 0.1)}`,
                transition: 'transform 0.2s',
                '&:hover': { transform: 'scale(1.02)' },
              }}>
                <img src={img.url} alt={img.name} style={{ width: '100%', display: 'block' }} />
                <Box sx={{ p: 1, bgcolor: alpha('#94A3B8', 0.04) }}>
                  <Typography variant="caption" noWrap>{img.name}</Typography>
                </Box>
              </Box>
            ))}
          </Box>
        </Paper>
        </Grow>
      )}

      {/* Audio files */}
      {audioFiles.length > 0 && (
        <Paper sx={{ p: 3, mb: 3, borderRadius: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <AudioFileRoundedIcon sx={{ color: '#F59E0B' }} /> Audio / Voiceover
          </Typography>
          {audioFiles.map((a) => (
            <Box key={a.path} sx={{
              display: 'flex', alignItems: 'center', gap: 2, mb: 1,
              p: 1.5, borderRadius: 2, bgcolor: alpha('#94A3B8', 0.04),
            }}>
              <Typography variant="body2" sx={{ flexGrow: 1 }}>{a.name}</Typography>
              <Chip label={formatSize(a.size)} size="small" variant="outlined" />
              <audio controls src={a.url} style={{ height: 32 }} />
            </Box>
          ))}
        </Paper>
      )}

      {/* Approve/Reject */}
      {canApprove && (
        <Paper sx={{
          p: 3, mb: 3, borderRadius: 3,
          border: `1px solid ${alpha('#6366F1', 0.2)}`,
        }}>
          <Typography variant="h6" sx={{ mb: 1 }}>Review Required</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Videos are ready. Approve to publish, or reject to discard. You can also review via Telegram bot.
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              startIcon={acting ? <CircularProgress size={16} /> : <CheckCircleRoundedIcon />}
              onClick={handleApprove}
              disabled={acting}
              sx={{ bgcolor: '#10B981', '&:hover': { bgcolor: '#059669' } }}
            >
              Approve & Publish
            </Button>
            <Button
              variant="outlined"
              color="error"
              startIcon={<CancelRoundedIcon />}
              onClick={handleReject}
              disabled={acting}
            >
              Reject
            </Button>
          </Box>
        </Paper>
      )}

      {/* All Output Files */}
      {files.length > 0 && (
        <Paper sx={{ p: 3, mb: 3, borderRadius: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
            <FolderRoundedIcon fontSize="small" /> All Output Files
          </Typography>
          {jobDir && (
            <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block', fontFamily: 'monospace' }}>
              📁 {jobDir}
            </Typography>
          )}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {files.map((f) => (
              <Box
                key={f.path}
                sx={{
                  display: 'flex', alignItems: 'center', gap: 1.5,
                  p: 1, borderRadius: 2,
                  bgcolor: alpha('#94A3B8', 0.04),
                  transition: 'background 0.15s',
                  '&:hover': { bgcolor: alpha('#6366F1', 0.06) },
                }}
              >
                {FILE_ICONS[f.type] || FILE_ICONS.other}
                <Typography variant="body2" sx={{ flexGrow: 1, fontFamily: 'monospace', fontSize: '0.8rem' }}>
                  {f.path}
                </Typography>
                <Chip label={formatSize(f.size)} size="small" variant="outlined" sx={{ minWidth: 70 }} />
                <Chip label={f.type} size="small" color={
                  f.type === 'video' ? 'primary' :
                  f.type === 'audio' ? 'warning' :
                  f.type === 'image' ? 'success' :
                  'default'
                } variant="outlined" sx={{ minWidth: 55 }} />
                <IconButton size="small" href={f.url} download title="Download">
                  <DownloadRoundedIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}
          </Box>
        </Paper>
      )}

      {/* Pipeline Progress */}
      {job.pipeline_result?.agent_results && (
        <Paper sx={{ p: 3, borderRadius: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
            Pipeline Progress
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {job.pipeline_result.agent_results.map((a: any, i: number) => (
              <Box
                key={i}
                sx={{
                  display: 'flex', alignItems: 'center', gap: 1.5,
                  p: 1, borderRadius: 2,
                  bgcolor: alpha('#94A3B8', 0.04),
                }}
              >
                <Chip
                  label={a.status}
                  size="small"
                  color={
                    a.status === 'success' ? 'success' :
                    a.status === 'failed' ? 'error' :
                    a.status === 'skipped' ? 'default' :
                    'warning'
                  }
                  variant="outlined"
                  sx={{ minWidth: 80 }}
                />
                <Typography variant="body2" fontWeight={500}>{a.agent}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
                  {a.elapsed_seconds ? `${a.elapsed_seconds.toFixed(1)}s` : ''}
                </Typography>
              </Box>
            ))}
          </Box>
        </Paper>
      )}
    </Box>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" fontWeight={500}>{label}</Typography>
      <Typography variant="body2" fontWeight={500}>{value}</Typography>
    </Box>
  );
}
