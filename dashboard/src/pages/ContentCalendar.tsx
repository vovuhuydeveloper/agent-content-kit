import { useState, useEffect } from 'react';
import {
  Box, Typography, Paper, Button, IconButton, TextField,
  Switch, Chip, Dialog, DialogTitle, DialogContent, DialogActions,
  FormControl, InputLabel, Select, MenuItem, CircularProgress,
  Tooltip, Grow,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded';
import CalendarTodayRoundedIcon from '@mui/icons-material/CalendarTodayRounded';
import ScheduleRoundedIcon from '@mui/icons-material/ScheduleRounded';
import api from '../services/api';

interface Schedule {
  id: string;
  name: string;
  cron_expression: string;
  timezone: string;
  enabled: boolean;
  source_url: string;
  language: string;
  niche: string;
  video_count: number;
  platforms: string[];
  run_count: number;
  last_run_at: string | null;
  next_run_at: string | null;
  last_job_id: string;
  created_at: string;
}

const CRON_PRESETS = [
  { label: 'Daily at 9 AM', value: '0 9 * * *' },
  { label: 'Mon & Thu', value: '0 9 * * 1,4' },
  { label: 'Every Monday', value: '0 9 * * 1' },
  { label: 'Every 3 days', value: '0 9 */3 * *' },
  { label: 'Weekly (Sunday)', value: '0 9 * * 0' },
];

export default function ContentCalendar() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({
    name: '',
    source_url: '',
    cron_expression: '0 9 * * 1',
    language: 'vi',
    niche: '',
    video_count: 3,
    platforms: ['tiktok', 'youtube'],
  });

  const fetchSchedules = async () => {
    setLoading(true);
    try {
      const res = await api.get('/schedules/');
      setSchedules(res.data.schedules || []);
    } catch (err) {
      console.error('Failed to load schedules:', err);
    }
    setLoading(false);
  };

  useEffect(() => { fetchSchedules(); }, []);

  const handleCreate = async () => {
    try {
      await api.post('/schedules/', form);
      setDialogOpen(false);
      setForm({ name: '', source_url: '', cron_expression: '0 9 * * 1', language: 'vi', niche: '', video_count: 3, platforms: ['tiktok', 'youtube'] });
      fetchSchedules();
    } catch (err) {
      console.error('Failed to create schedule:', err);
    }
  };

  const handleToggle = async (id: string) => {
    try { await api.post(`/schedules/${id}/toggle`); fetchSchedules(); }
    catch (err) { console.error('Toggle failed:', err); }
  };

  const handleDelete = async (id: string) => {
    if (confirm('Delete this schedule?')) {
      await api.delete(`/schedules/${id}`);
      fetchSchedules();
    }
  };

  const handleRunNow = async (id: string) => {
    try { await api.post(`/schedules/${id}/run-now`); fetchSchedules(); }
    catch (err) { console.error('Run failed:', err); }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 0.5 }}>Content Calendar</Typography>
          <Typography variant="body2" color="text.secondary">
            Schedule automated content creation
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <IconButton onClick={fetchSchedules} size="small" sx={{ color: 'text.secondary', transition: 'all 0.3s', '&:hover': { transform: 'rotate(180deg)', color: 'primary.main' } }}>
            <RefreshRoundedIcon fontSize="small" />
          </IconButton>
          <Button variant="contained" startIcon={<AddRoundedIcon />} onClick={() => setDialogOpen(true)} size="small">
            New Schedule
          </Button>
        </Box>
      </Box>

      {loading ? (
        <Box sx={{ textAlign: 'center', py: 10 }}>
          <CircularProgress size={32} sx={{ color: '#6366F1' }} />
        </Box>
      ) : schedules.length === 0 ? (
        <Paper sx={{
          p: 8, textAlign: 'center', borderRadius: 4,
          border: '1px dashed rgba(148, 163, 184, 0.15)', bgcolor: 'transparent',
        }}>
          <CalendarTodayRoundedIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.4 }} />
          <Typography variant="h6" color="text.secondary" sx={{ mb: 0.5 }}>
            No schedules yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Automate your content creation pipeline
          </Typography>
          <Button variant="contained" startIcon={<AddRoundedIcon />} onClick={() => setDialogOpen(true)}>
            Create first schedule
          </Button>
        </Paper>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {schedules.map((s) => (
            <Grow in timeout={300 + schedules.indexOf(s) * 80} key={s.id}>
            <Paper
              sx={{
                p: 2.5, borderRadius: 3,
                borderLeft: s.enabled ? '3px solid #10B981' : undefined,
                opacity: s.enabled ? 1 : 0.55,
                transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': { transform: 'translateY(-2px)', boxShadow: '0 8px 24px rgba(15,23,42,0.06)' },
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{
                  width: 40, height: 40, borderRadius: '10px',
                  bgcolor: s.enabled ? alpha('#10B981', 0.08) : alpha('#64748B', 0.08),
                  color: s.enabled ? '#10B981' : '#64748B',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <ScheduleRoundedIcon sx={{ fontSize: 20 }} />
                </Box>

                <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                  <Typography variant="subtitle1" fontWeight={600}>{s.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {s.cron_expression} · {s.video_count} videos · {s.platforms.join(', ')}
                  </Typography>
                  <br />
                  <Typography variant="caption" color="text.secondary">
                    {s.source_url.slice(0, 50)} · {s.run_count} runs
                    {s.next_run_at && ` · Next: ${new Date(s.next_run_at).toLocaleDateString()}`}
                  </Typography>
                </Box>

                <Chip
                  label={s.enabled ? 'Active' : 'Paused'}
                  size="small"
                  color={s.enabled ? 'success' : 'default'}
                  variant="outlined"
                  sx={{ fontWeight: 500 }}
                />

                <Tooltip title="Run now">
                  <IconButton size="small" onClick={() => handleRunNow(s.id)}
                    sx={{ color: '#6366F1', '&:hover': { bgcolor: alpha('#6366F1', 0.08) } }}>
                    <PlayArrowRoundedIcon fontSize="small" />
                  </IconButton>
                </Tooltip>

                <Switch checked={s.enabled} onChange={() => handleToggle(s.id)} size="small" />

                <IconButton size="small" onClick={() => handleDelete(s.id)}
                  sx={{ color: '#64748B', '&:hover': { color: '#EF4444' } }}>
                  <DeleteOutlineRoundedIcon fontSize="small" />
                </IconButton>
              </Box>
            </Paper>
            </Grow>
          ))}
        </Box>
      )}

      {/* Create Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>New Content Schedule</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField label="Schedule name" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} fullWidth required />
            <TextField label="Source URL" value={form.source_url}
              onChange={(e) => setForm({ ...form, source_url: e.target.value })} fullWidth required />
            <FormControl fullWidth>
              <InputLabel>Frequency</InputLabel>
              <Select value={form.cron_expression}
                onChange={(e) => setForm({ ...form, cron_expression: e.target.value as string })} label="Frequency">
                {CRON_PRESETS.map((p) => (
                  <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField label="Videos" type="number" value={form.video_count}
                onChange={(e) => setForm({ ...form, video_count: parseInt(e.target.value) })} sx={{ width: 120 }} />
              <FormControl sx={{ flex: 1 }}>
                <InputLabel>Language</InputLabel>
                <Select value={form.language}
                  onChange={(e) => setForm({ ...form, language: e.target.value as string })} label="Language">
                  <MenuItem value="vi">Tiếng Việt</MenuItem>
                  <MenuItem value="en">English</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <TextField label="Niche / Topic" value={form.niche}
              onChange={(e) => setForm({ ...form, niche: e.target.value })} fullWidth />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setDialogOpen(false)} sx={{ color: 'text.secondary' }}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={!form.name || !form.source_url}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
