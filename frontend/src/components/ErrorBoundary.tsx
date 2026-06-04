import { Component, type ErrorInfo, type ReactNode } from "react";
import { Container, Title, Text, Button } from "@mantine/core";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Container py="xl">
          <Title order={2} mb="sm">
            Something went wrong
          </Title>
          <Text c="dimmed" mb="md">
            {this.state.error?.message ?? "An unexpected error occurred."}
          </Text>
          <Button onClick={() => window.location.reload()}>Reload</Button>
        </Container>
      );
    }
    return this.props.children;
  }
}
