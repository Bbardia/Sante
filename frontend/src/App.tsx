import { useQuery } from "@tanstack/react-query";
import { Container, Title, Text, Badge, Loader } from "@mantine/core";
import { getHealth } from "./api/client";

export default function App() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
  });

  return (
    <Container p="xl">
      <Title order={1}>Santé</Title>
      <Text mt="md">
        Backend status:{" "}
        {isLoading && <Loader size="xs" />}
        {isError && <Badge color="red">unreachable</Badge>}
        {data && <Badge color="green">{data.status}</Badge>}
      </Text>
    </Container>
  );
}
