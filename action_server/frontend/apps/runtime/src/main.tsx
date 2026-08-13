import { createRoot } from 'react-dom/client';
import { App } from '../../../src/App';
import '../../../src/index.css';

const container = document.getElementById('root');

if (container) {
  createRoot(container).render(<App />);
}
