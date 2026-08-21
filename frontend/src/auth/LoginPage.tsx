import { useState } from "react";
import { useForm } from "@mantine/form";
import {
  Center,
  Card,
  Title,
  TextInput,
  PasswordInput,
  Button,
  Alert,
  Stack,
} from "@mantine/core";
import { useAuth } from "./AuthContext";
import { ApiError } from "../api/client";

export default function LoginPage() {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const form = useForm({
    initialValues: { username: "", password: "" },
    validate: {
      username: (v) => (v.trim().length === 0 ? "Username is required" : null),
      password: (v) => (v.length === 0 ? "Password is required" : null),
    },
  });

  async function handleSubmit(values: { username: string; password: string }) {
    setError(null);
    setLoading(true);
    try {
      await login(values.username, values.password);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Center h="100vh">
      <Card shadow="md" padding="xl" radius="md" w={360}>
        <Title order={2} mb="lg" ta="center">
          Santé
        </Title>
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack>
            {error && (
              <Alert color="red" title="Login failed">
                {error}
              </Alert>
            )}
            <TextInput
              label="Username"
              placeholder="Enter username"
              {...form.getInputProps("username")}
            />
            <PasswordInput
              label="Password"
              placeholder="Enter password"
              {...form.getInputProps("password")}
            />
            <Button type="submit" loading={loading} fullWidth mt="sm">
              Sign In
            </Button>
          </Stack>
        </form>
      </Card>
    </Center>
  );
}
