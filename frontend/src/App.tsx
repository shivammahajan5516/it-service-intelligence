import { Route, Routes } from "react-router-dom";
import { FiltersProvider } from "./context/FiltersContext";
import { Layout } from "./components/Layout";
import Overview from "./pages/Overview";
import SlaPerformance from "./pages/SlaPerformance";
import RootCauses from "./pages/RootCauses";
import TeamPerformance from "./pages/TeamPerformance";
import Customers from "./pages/Customers";
import TicketsPage from "./pages/Tickets";
import DataQualityPage from "./pages/DataQuality";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <FiltersProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/sla" element={<SlaPerformance />} />
          <Route path="/root-causes" element={<RootCauses />} />
          <Route path="/teams" element={<TeamPerformance />} />
          <Route path="/customers" element={<Customers />} />
          <Route path="/tickets" element={<TicketsPage />} />
          <Route path="/data-quality" element={<DataQualityPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Layout>
    </FiltersProvider>
  );
}
