import { useCallback } from 'react';
import {
  Box, Typography, Paper, IconButton, Avatar, Alert,
} from '@mui/material';
import { useDropzone } from 'react-dropzone';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DeleteIcon from '@mui/icons-material/Delete';
import ImageIcon from '@mui/icons-material/Image';
import type { WizardData } from '../../pages/SetupWizard';

interface Props {
  data: WizardData;
  update: (d: Partial<WizardData>) => void;
}

export default function AssetStep({ data, update }: Props) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      update({ characterFiles: [...data.characterFiles, ...accepted] });
    },
    [data.characterFiles, update]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.png', '.jpg', '.jpeg', '.webp'] },
    maxSize: 10 * 1024 * 1024,
  });

  const removeFile = (i: number) =>
    update({ characterFiles: data.characterFiles.filter((_, idx) => idx !== i) });

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <ImageIcon color="primary" /> Character / Assets
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Upload character images that will appear in your videos. PNG with transparent background works best.
      </Typography>

      {/* Dropzone */}
      <Paper
        {...getRootProps()}
        sx={{
          p: 4,
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'rgba(15, 23, 42, 0.1)',
          borderRadius: 3,
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s',
          bgcolor: isDragActive ? 'rgba(99, 102, 241, 0.06)' : 'transparent',
          '&:hover': {
            borderColor: 'primary.light',
            bgcolor: 'rgba(99, 102, 241, 0.03)',
          },
        }}
      >
        <input {...getInputProps()} />
        <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.light', mb: 1 }} />
        <Typography variant="body1" fontWeight={500}>
          {isDragActive ? 'Drop images here...' : 'Drag images here or click to select'}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          PNG, JPG, WebP — max 10MB
        </Typography>
      </Paper>

      {/* Preview */}
      {data.characterFiles.length > 0 && (
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {data.characterFiles.map((file, i) => (
            <Paper
              key={i}
              sx={{
                p: 1, position: 'relative',
                bgcolor: 'rgba(15, 23, 42, 0.02)',
                borderRadius: 2,
              }}
            >
              <Avatar
                src={URL.createObjectURL(file)}
                variant="rounded"
                sx={{ width: 80, height: 80 }}
              />
              <Typography
                variant="caption"
                noWrap
                sx={{ display: 'block', maxWidth: 80, mt: 0.5, textAlign: 'center' }}
              >
                {file.name}
              </Typography>
              <IconButton
                size="small"
                onClick={() => removeFile(i)}
                sx={{
                  position: 'absolute', top: -8, right: -8,
                  bgcolor: 'error.main', color: 'white',
                  width: 22, height: 22,
                  '&:hover': { bgcolor: 'error.dark' },
                }}
              >
                <DeleteIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </Paper>
          ))}
        </Box>
      )}

      <Alert severity="success" sx={{ borderRadius: 3 }}>
        This step is optional. If no assets are uploaded, the system will use default rendering.
      </Alert>
    </Box>
  );
}
