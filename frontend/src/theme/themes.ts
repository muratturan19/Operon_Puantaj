import { createTheme } from '@mui/material/styles'

// kolektif360 marka paleti — E:\Mira\Kolektif360\Tasarim_İlkeleri\kolektif360_brand_guide.md
const NAVY = '#1c2536'
const ORANGE = '#f47c20'
const ORANGE_LIGHT = '#ffa15e'
const ORANGE_DEEP = '#d96710'
const BG_PAGE = '#e8eaed'
const TEXT_MID = '#4a5568'
const TEXT_LIGHT = '#718096'
const BORDER = '#e2e8f0'
const SUCCESS = '#2f855a'
const WARNING = '#d97706'
const DANGER = '#c53030'

export const theme = createTheme({
  palette: {
    primary: { main: ORANGE, light: ORANGE_LIGHT, dark: ORANGE_DEEP, contrastText: '#ffffff' },
    secondary: { main: NAVY, contrastText: '#ffffff' },
    success: { main: SUCCESS },
    warning: { main: WARNING },
    error: { main: DANGER },
    background: { default: BG_PAGE, paper: '#ffffff' },
    text: { primary: NAVY, secondary: TEXT_MID, disabled: TEXT_LIGHT },
    divider: BORDER,
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: '"Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif',
    h1: { fontWeight: 600, letterSpacing: '-0.02em' },
    h2: { fontWeight: 600, letterSpacing: '-0.02em' },
    h3: { fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  transitions: {
    easing: {
      sharp: 'cubic-bezier(0.23, 1, 0.32, 1)',
    },
    duration: {
      shortest: 150,
      shorter: 200,
      short: 250,
      standard: 300,
    },
  },
  components: {
    // Tasarım sistemi: kart 8px ama buton 3-4px (köşeli görünüm) — global shape.borderRadius
    // butona sızmasın diye ayrı override (kolektif360_design_system.html §05 Düzen).
    MuiButton: {
      styleOverrides: {
        root: ({ theme: t }) => ({
          borderRadius: 4,
          transition: t.transitions.create('transform', { duration: 160 }),
          '&:active': { transform: 'scale(0.97)' },
        }),
      },
    },
    // Rozet (status-badge) 3px köşe, MUI'nin varsayılan hap-şekli DEĞİL.
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 3 },
      },
    },
  },
})
