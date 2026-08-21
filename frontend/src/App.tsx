import { Center, Loader } from "@mantine/core";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import LoginPage from "./auth/LoginPage";
import AppLayout from "./layout/AppLayout";

function AppInner() {
  const { user, loading } = useAuth();
  if (loading) return <Center style={{ height: "100vh" }}><Loader /></Center>;
  return user ? <AppLayout /> : <LoginPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}
