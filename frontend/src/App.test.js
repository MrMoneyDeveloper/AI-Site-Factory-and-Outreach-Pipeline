import { fireEvent, render, screen } from '@testing-library/react';
import axios from 'axios';
import App from './App';

jest.mock('axios');

beforeEach(() => {
  jest.resetAllMocks();
  axios.get.mockImplementation((url) => Promise.resolve({ data:
    url.endsWith('/api/config/status')
      ? { apifyConfigured: false, netlifyConfigured: false, defaultLocationQuery: 'Durban, South Africa' }
      : [{ id: 'plumbers', label: 'Plumbers', inputTemplate: { searchStringsArray: ['plumbers'] } }]
  }));
});

test('loads presets and explains missing configuration without sending work', async () => {
  render(<App />);
  expect(await screen.findByText('Plumbers')).toBeInTheDocument();
  expect(screen.getByText('Configuration required')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Deploy selected' })).toBeDisabled();
  expect(axios.post).not.toHaveBeenCalled();
});

test('requires a selected industry before scraping', async () => {
  render(<App />);
  await screen.findByText('Plumbers');
  fireEvent.click(screen.getByRole('button', { name: 'Clear all' }));
  fireEvent.click(screen.getByRole('button', { name: 'Run Apify scrape' }));
  expect(screen.getByText('No industry selected')).toBeInTheDocument();
  expect(axios.post).not.toHaveBeenCalled();
});

test('shows a backend connection failure', async () => {
  axios.get.mockRejectedValue(new Error('offline'));
  render(<App />);
  expect(await screen.findByText('Backend connection failed')).toBeInTheDocument();
});
