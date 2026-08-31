import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Overview from './pages/Overview';
import Docs from './pages/Docs';
import Abstractions from './pages/Abstractions';
import Research from './pages/Research';
import Architecture from './pages/Architecture';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="/overview" element={<Overview />} />
          <Route path="/docs" element={<Docs />} />
          <Route path="/abstractions" element={<Abstractions />} />
          <Route path="/research" element={<Research />} />
          <Route path="/architecture" element={<Architecture />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
