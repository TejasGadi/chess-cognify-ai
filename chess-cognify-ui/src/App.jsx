import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import Home from '@/pages/Home';
import AnalysisDashboard from '@/pages/AnalysisDashboard';
import GameView from '@/pages/GameView';
import BooksApp from '@/pages/BooksApp';

function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/analysis" element={<AnalysisDashboard />} />
          <Route path="/analysis/:gameId" element={<GameView />} />
          <Route path="/books" element={<BooksApp />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;

