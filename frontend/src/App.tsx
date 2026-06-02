import { AuthProvider, useAuth } from "./auth/AuthContext";
import LoginPage from "./auth/LoginPage";
import AppLayout from "./layout/AppLayout";

function AppInner() {
  const { user } = useAuth();
  if (user === null) return <LoginPage />;
  return <AppLayout />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}
