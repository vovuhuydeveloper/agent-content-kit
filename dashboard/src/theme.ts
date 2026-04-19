import { createTheme, alpha } from '@mui/material/styles';

// Light professional palette
const palette = {
  primary: '#6366F1',    // Indigo
  secondary: '#10B981',  // Emerald
  accent: '#F59E0B',     // Amber
  danger: '#EF4444',
  surface: '#F8FAFC',    // Slate 50
  card: '#FFFFFF',
  cardHover: '#F1F5F9',  // Slate 100
  border: 'rgba(15, 23, 42, 0.08)',
  borderHover: 'rgba(15, 23, 42, 0.15)',
  text: '#0F172A',       // Slate 900
  textMuted: '#64748B',  // Slate 500
  textDim: '#94A3B8',    // Slate 400
  navBg: '#FFFFFF',
};

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: palette.primary,
      light: '#818CF8',
      dark: '#4F46E5',
    },
    secondary: {
      main: palette.secondary,
      light: '#34D399',
      dark: '#059669',
    },
    background: {
      default: palette.surface,
      paper: palette.card,
    },
    text: {
      primary: palette.text,
      secondary: palette.textMuted,
    },
    error: { main: palette.danger },
    warning: { main: palette.accent },
    success: { main: palette.secondary },
    info: { main: '#3B82F6' },
    divider: palette.border,
  },
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h4: { fontWeight: 700, fontSize: '1.75rem', letterSpacing: '-0.025em', lineHeight: 1.2 },
    h5: { fontWeight: 600, fontSize: '1.25rem', letterSpacing: '-0.015em' },
    h6: { fontWeight: 600, fontSize: '1.1rem', letterSpacing: '-0.01em' },
    subtitle1: { fontWeight: 500, fontSize: '0.95rem' },
    subtitle2: { fontWeight: 600, fontSize: '0.8rem', letterSpacing: '0.02em', textTransform: 'uppercase' as const },
    body2: { fontSize: '0.875rem', lineHeight: 1.5 },
    caption: { fontSize: '0.75rem', lineHeight: 1.4 },
    button: { fontWeight: 600, textTransform: 'none' as const, letterSpacing: '0.01em' },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { background: palette.surface },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: palette.card,
          border: `1px solid ${palette.border}`,
          borderRadius: 16,
          boxShadow: '0 1px 3px rgba(15, 23, 42, 0.04)',
          transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            borderColor: palette.borderHover,
            boxShadow: '0 4px 16px rgba(15, 23, 42, 0.08)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: palette.card,
          border: `1px solid ${palette.border}`,
          borderRadius: 16,
          boxShadow: '0 1px 3px rgba(15, 23, 42, 0.04)',
          transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          padding: '8px 20px',
          fontSize: '0.875rem',
          transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        },
        contained: {
          boxShadow: `0 2px 8px ${alpha(palette.primary, 0.25)}`,
          '&:hover': {
            boxShadow: `0 4px 16px ${alpha(palette.primary, 0.35)}`,
            transform: 'translateY(-1px)',
          },
          '&:active': {
            transform: 'translateY(0)',
          },
        },
        outlined: {
          borderColor: palette.border,
          '&:hover': {
            borderColor: palette.borderHover,
            backgroundColor: alpha(palette.primary, 0.04),
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 10,
            transition: 'box-shadow 0.2s ease',
            '& fieldset': { borderColor: palette.border, transition: 'border-color 0.2s ease' },
            '&:hover fieldset': { borderColor: palette.borderHover },
            '&.Mui-focused': {
              boxShadow: `0 0 0 3px ${alpha(palette.primary, 0.1)}`,
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
          fontSize: '0.75rem',
          transition: 'all 0.15s ease',
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          transition: 'all 0.2s ease',
        },
      },
    },
    MuiStepper: {
      styleOverrides: {
        root: { padding: '24px 0' },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          height: 6,
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundColor: palette.card,
          border: `1px solid ${palette.border}`,
          borderRadius: 20,
          boxShadow: '0 25px 50px rgba(15, 23, 42, 0.15)',
        },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        root: {
          '& .MuiSwitch-track': {
            transition: 'background-color 0.3s ease',
          },
        },
      },
    },
  },
});

export default theme;
export { palette };
