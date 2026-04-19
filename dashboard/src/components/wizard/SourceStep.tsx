import { useState } from 'react';
import {
  Box, TextField, Typography, Select, MenuItem, FormControl,
  InputLabel, Alert, Switch, FormControlLabel, Collapse, Paper, Chip,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import LinkRoundedIcon from '@mui/icons-material/LinkRounded';
import ScheduleRoundedIcon from '@mui/icons-material/ScheduleRounded';
import CalendarMonthRoundedIcon from '@mui/icons-material/CalendarMonthRounded';
import type { WizardData } from '../../pages/SetupWizard';

interface Props {
  data: WizardData;
  update: (d: Partial<WizardData>) => void;
}

const FREQUENCIES = [
  { value: 'daily', label: 'Daily', desc: '1 batch every day', icon: '📅' },
  { value: 'weekdays', label: 'Weekdays', desc: 'Mon–Fri only', icon: '💼' },
  { value: '3x_week', label: '3x / week', desc: 'Mon, Wed, Fri', icon: '📊' },
  { value: 'weekly', label: 'Weekly', desc: 'Once per week', icon: '📆' },
];

export default function SourceStep({ data, update }: Props) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <LinkRoundedIcon color="primary" /> Content Source
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Enter a URL to any content — website, YouTube, TikTok, or article.
        The system will automatically crawl and analyze it.
      </Typography>

      <TextField
        label="Source URL"
        placeholder="https://example.com/article or YouTube URL"
        value={data.sourceUrl}
        onChange={(e) => update({ sourceUrl: e.target.value })}
        fullWidth
        variant="outlined"
        InputProps={{
          startAdornment: <LinkRoundedIcon sx={{ mr: 1, color: 'text.secondary' }} />,
        }}
      />

      <TextField
        label="Domain / Niche"
        placeholder="Leave empty for auto-detect from content"
        value={data.niche}
        onChange={(e) => update({ niche: e.target.value })}
        fullWidth
        helperText="e.g. education, tech, cooking, fitness"
      />

      <Box sx={{ display: 'flex', gap: 2 }}>
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Language</InputLabel>
          <Select
            value={data.language}
            onChange={(e) => update({ language: e.target.value })}
            label="Language"
          >
            <MenuItem value="en">🇺🇸 English</MenuItem>
            <MenuItem value="vi">🇻🇳 Vietnamese</MenuItem>
            <MenuItem value="ja">🇯🇵 Japanese</MenuItem>
            <MenuItem value="ko">🇰🇷 Korean</MenuItem>
            <MenuItem value="zh">🇨🇳 Chinese</MenuItem>
          </Select>
        </FormControl>

        <FormControl sx={{ minWidth: 130 }}>
          <InputLabel>Videos</InputLabel>
          <Select
            value={data.videoCount}
            onChange={(e) => update({ videoCount: Number(e.target.value) })}
            label="Videos"
          >
            {[1, 2, 3, 5, 10].map((n) => (
              <MenuItem key={n} value={n}>{n} video{n > 1 ? 's' : ''}</MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl sx={{ minWidth: 140 }}>
          <InputLabel>Aspect Ratio</InputLabel>
          <Select
            value={data.aspectRatio}
            onChange={(e) => update({ aspectRatio: e.target.value })}
            label="Aspect Ratio"
          >
            <MenuItem value="9:16">📱 9:16 (Shorts)</MenuItem>
            <MenuItem value="16:9">🖥️ 16:9 (YouTube)</MenuItem>
            <MenuItem value="1:1">⬜ 1:1 (Square)</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Schedule Section */}
      <Paper sx={{
        p: 2.5, borderRadius: 3,
        bgcolor: data.scheduleEnabled ? alpha('#6366F1', 0.04) : alpha('#94A3B8', 0.03),
        border: data.scheduleEnabled ? `1px solid ${alpha('#6366F1', 0.15)}` : '1px solid transparent',
        transition: 'all 0.3s ease',
      }}>
        <FormControlLabel
          control={
            <Switch
              checked={data.scheduleEnabled}
              onChange={(e) => update({ scheduleEnabled: e.target.checked })}
              color="primary"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ScheduleRoundedIcon sx={{ fontSize: 20, color: data.scheduleEnabled ? 'primary.main' : 'text.secondary' }} />
              <Typography variant="subtitle2" fontWeight={600}>
                Auto-schedule
              </Typography>
              <Chip label="Optional" size="small" variant="outlined" sx={{ height: 20, fontSize: '0.65rem' }} />
            </Box>
          }
        />
        <Typography variant="caption" color="text.secondary" sx={{ ml: 5.5, display: 'block' }}>
          Automatically create videos on a recurring schedule
        </Typography>

        <Collapse in={data.scheduleEnabled}>
          <Box sx={{ mt: 2, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
            {FREQUENCIES.map((freq) => {
              const selected = data.scheduleFrequency === freq.value;
              return (
                <Paper
                  key={freq.value}
                  onClick={() => update({ scheduleFrequency: freq.value })}
                  sx={{
                    p: 1.5, cursor: 'pointer', borderRadius: 2,
                    border: selected ? `2px solid ${alpha('#6366F1', 0.4)}` : '2px solid transparent',
                    bgcolor: selected ? alpha('#6366F1', 0.06) : alpha('#94A3B8', 0.04),
                    transition: 'all 0.2s ease',
                    '&:hover': { bgcolor: alpha('#6366F1', 0.08), transform: 'translateY(-1px)' },
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography sx={{ fontSize: '1.1rem' }}>{freq.icon}</Typography>
                    <Box>
                      <Typography variant="body2" fontWeight={600}>{freq.label}</Typography>
                      <Typography variant="caption" color="text.secondary">{freq.desc}</Typography>
                    </Box>
                  </Box>
                </Paper>
              );
            })}
          </Box>

          {/* Time picker */}
          <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
            <TextField
              label="Run at"
              type="time"
              value={data.scheduleTime}
              onChange={(e) => update({ scheduleTime: e.target.value })}
              size="small"
              sx={{ width: 140 }}
              InputLabelProps={{ shrink: true }}
              inputProps={{ step: 1800 }} // 30 min steps
            />
            <Typography variant="caption" color="text.secondary">
              Your local timezone ({Intl.DateTimeFormat().resolvedOptions().timeZone})
            </Typography>
          </Box>

          <Alert severity="info" icon={<CalendarMonthRoundedIcon />} sx={{ mt: 2, borderRadius: 2 }}>
            <Typography variant="caption">
              Pipeline will run {data.scheduleFrequency === 'daily' ? 'every day' :
                data.scheduleFrequency === 'weekdays' ? 'Monday–Friday' :
                data.scheduleFrequency === '3x_week' ? 'Mon, Wed, Fri' :
                'once a week'} at <strong>{data.scheduleTime}</strong> and create {data.videoCount} video{data.videoCount > 1 ? 's' : ''} per batch.
              You can manage schedules from the <strong>Calendar</strong> page.
            </Typography>
          </Alert>
        </Collapse>
      </Paper>

      <Alert severity="info" sx={{ borderRadius: 3 }}>
        Supported sources: Website (blog, news), YouTube, TikTok, Google Docs, PDF link
      </Alert>
    </Box>
  );
}
