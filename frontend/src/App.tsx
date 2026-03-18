import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainLayout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Mixer from './pages/Mixer';
import Stitcher from './pages/Stitcher';
import Extractor from './pages/Extractor';
import './App.css';
import './pages/Dashboard.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="mixer" element={<Mixer />} />
          <Route path="stitcher" element={<Stitcher />} />
          <Route path="extractor" element={<Extractor />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;

