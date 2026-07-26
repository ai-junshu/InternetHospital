import { Navigate, Route, Routes } from 'react-router-dom'
import BasicLayout from './layouts/BasicLayout'
import AuthRoute from './components/AuthRoute'
import LoginPage from './routes/login'
import StoreAdmin from './routes/store'
import CustomerAdmin from './routes/customer'
import RepurchaseAdmin from './routes/repurchase'
import RiskAdmin from './routes/risk'
import DataAdmin from './routes/data'
import PlatAdmin, { PlatIndex } from './routes/plat'
import AiModelsAdmin from './routes/plat/ai-models'
import DataAssetsAdmin from './routes/plat/data-assets'
import ComplianceBrain from './routes/plat/compliance'
import DataGovernance from './routes/plat/data-governance'
import IhIndex from './routes/ih'
import IhHospital from './routes/ih/hospital'
import IhOperations from './routes/ih/operations'
import DrugCatalogAdmin from './routes/ih/drug-catalog'
import ComplianceReview from './routes/plat/compliance-review'
import TherapistIndex from './routes/therapist'
import TherapistCustomers from './routes/therapist/customers'
import TherapistPlans from './routes/therapist/plans'
import TherapistRecords from './routes/therapist/records'
import TherapistAdherence from './routes/therapist/adherence'
import IhSupervision from './routes/plat/ih-supervision'
import SalesSupervision from './routes/plat/sales-supervision'
import DataAssetDashboard from './routes/plat/data-asset-dashboard'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <AuthRoute>
            <BasicLayout />
          </AuthRoute>
        }
      >
        <Route index element={<Navigate to="/customer" replace />} />
        <Route path="store" element={<StoreAdmin />} />
        <Route path="customer" element={<CustomerAdmin />} />
        <Route path="repurchase" element={<RepurchaseAdmin />} />
        <Route path="risk" element={<RiskAdmin />} />
        <Route path="data" element={<DataAdmin />} />
        <Route path="ih" element={<IhIndex />}>
          <Route index element={<IhHospital />} />
          <Route path="hospital" element={<IhHospital />} />
          <Route path="operations" element={<IhOperations />} />
          <Route path="drug-catalog" element={<DrugCatalogAdmin />} />
        </Route>
        <Route path="therapist" element={<TherapistIndex />}>
          <Route index element={<TherapistCustomers />} />
          <Route path="customers" element={<TherapistCustomers />} />
          <Route path="plans" element={<TherapistPlans />} />
          <Route path="records" element={<TherapistRecords />} />
          <Route path="adherence" element={<TherapistAdherence />} />
        </Route>
        <Route path="plat" element={<PlatAdmin />}>
          <Route index element={<PlatIndex />} />
          <Route path="ai-models" element={<AiModelsAdmin />} />
          <Route path="data-assets" element={<DataAssetsAdmin />} />
          <Route path="compliance" element={<ComplianceBrain />} />
          <Route path="data-governance" element={<DataGovernance />} />
          <Route path="ih-supervision" element={<IhSupervision />} />
          <Route path="sales-supervision" element={<SalesSupervision />} />
          <Route path="data-asset-dashboard" element={<DataAssetDashboard />} />
          <Route path="compliance-review" element={<ComplianceReview />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
