import { useQuery } from "@tanstack/react-query";
import {
  SimpleGrid,
  Paper,
  Text,
  Title,
  Loader,
  Alert,
  Table,
  Badge,
  Stack,
  Group,
} from "@mantine/core";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import { getDashboard } from "../api/client";

export default function DashboardPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  if (isLoading) {
    return (
      <Group justify="center" mt="xl">
        <Loader />
      </Group>
    );
  }

  if (isError) {
    return (
      <Alert color="red" title="Failed to load dashboard" mt="md">
        {error instanceof Error ? error.message : "Unknown error"}
      </Alert>
    );
  }

  const { today, top_products, low_stock } = data!;

  return (
    <Stack gap="xl">
      <Title order={2}>Dashboard</Title>

      {/* ── Stat cards ── */}
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <Paper withBorder p="lg" radius="md">
          <Text size="xs" tt="uppercase" fw={700} c="dimmed" mb={4}>
            Today's Revenue
          </Text>
          <Text size="xl" fw={700}>
            {today.revenue.toFixed(2)}
          </Text>
        </Paper>

        <Paper withBorder p="lg" radius="md">
          <Text size="xs" tt="uppercase" fw={700} c="dimmed" mb={4}>
            Today's Sales
          </Text>
          <Text size="xl" fw={700}>
            {today.sales_count}
          </Text>
        </Paper>
      </SimpleGrid>

      {/* ── Top products bar chart ── */}
      <Paper withBorder p="lg" radius="md">
        <Title order={4} mb="md">
          Top Products (last 30 days)
        </Title>
        {top_products.length === 0 ? (
          <Text c="dimmed" size="sm">
            No sales yet.
          </Text>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={top_products} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
              <XAxis dataKey="product" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="qty" fill="#228be6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Paper>

      {/* ── Low stock alerts ── */}
      <Paper withBorder p="lg" radius="md">
        <Title order={4} mb="md">
          Low Stock
        </Title>
        {low_stock.length === 0 ? (
          <Text c="green" size="sm" fw={500}>
            All stock levels are healthy.
          </Text>
        ) : (
          <Table striped highlightOnHover withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Ingredient</Table.Th>
                <Table.Th>Qty</Table.Th>
                <Table.Th>Reorder Level</Table.Th>
                <Table.Th>Unit</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {low_stock.map((item) => (
                <Table.Tr key={item.name}>
                  <Table.Td>{item.name}</Table.Td>
                  <Table.Td style={{ color: "var(--mantine-color-red-6)", fontWeight: 600 }}>
                    {item.qty}
                  </Table.Td>
                  <Table.Td>{item.reorder_level}</Table.Td>
                  <Table.Td>{item.unit}</Table.Td>
                  <Table.Td>
                    <Badge color="red" variant="filled" size="sm">
                      LOW
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
    </Stack>
  );
}
