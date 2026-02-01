import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import Home from '@/pages/Home';
import AnalysisDashboard from '@/pages/AnalysisDashboard';
import GameView from '@/pages/GameView';
import BooksList from '@/pages/BooksList';
import BooksUpload from '@/pages/BooksUpload';
import BookChat from '@/pages/BookChat';
import SelfAnalysisPage from '@/pages/SelfAnalysisPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/analysis" element={<AnalysisDashboard />} />
          <Route path="/analysis/:gameId" element={<GameView />} />
          <Route path="/tools/analysis" element={<SelfAnalysisPage />} />
          <Route path="/books" element={<BooksList />} />
          <Route path="/books/upload" element={<BooksUpload />} />
          <Route path="/books/:bookId" element={<BookChat />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;

