import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Title,
  TextInput,
  Button,
  Group,
  Table,
  Modal,
  Stack,
  Text,
  Box,
  Badge,
  Paper,
} from "@mantine/core";
import {
  listSales,
  getReceipt,
} from "../api/client";
import ReceiptView from "../components/ReceiptView";

export default function HistoryPage() {
  const [search, setSearch] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data: sales = [], isLoading } = useQuery({
    queryKey: ["sales", search, start, end],
    queryFn: () => listSales({ search, start, end }),
  });

  const { data: receipt, isError: receiptIsError } = useQuery({
    queryKey: ["receipt", selectedId],
    queryFn: () => getReceipt(selectedId!),
    enabled: selectedId !== null,
  });

  const totalRevenue = sales.reduce((sum, s) => sum + s.total, 0);

  function handleClear() {
    setSearch("");
    setStart("");
    setEnd("");
  }

  return (
    <Box>
      <Title order={3} mb="md">Sales History</Title>

      {/* Filters */}
      <Paper withBorder p="md" radius="sm" mb="md">
        <Group align="flex-end" gap="sm" wrap="wrap">
          <TextInput
            label="Search"
            placeholder="product or customer"
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            style={{ flex: 1, minWidth: 160 }}
          />
          <TextInput
            label="From"
            type="date"
            value={start}
            onChange={(e) => setStart(e.currentTarget.value)}
            style={{ width: 160 }}
          />
          <TextInput
            label="To"
            type="date"
            value={end}
            onChange={(e) => setEnd(e.currentTarget.value)}
            style={{ width: 160 }}
          />
          <Button variant="light" onClick={handleClear}>
            Clear
          </Button>
        </Group>
      </Paper>

      {/* Summary */}
      <Group justify="flex-end" mb="xs">
        <Text size="sm" c="dimmed">Total revenue:</Text>
        <Text fw={600}>{totalRevenue.toFixed(2)}</Text>
      </Group>

      {/* Table */}
      <Paper withBorder radius="sm">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>#</Table.Th>
              <Table.Th>Date</Table.Th>
              <Table.Th>Customer</Table.Th>
              <Table.Th>Items</Table.Th>
              <Table.Th>Total</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading && (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text c="dimmed" size="sm">Loading…</Text>
                </Table.Td>
              </Table.Tr>
            )}
            {!isLoading && sales.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text c="dimmed" size="sm">No sales found.</Text>
                </Table.Td>
              </Table.Tr>
            )}
            {sales.map((sale) => (
              <Table.Tr
                key={sale.id}
                style={{ cursor: "pointer" }}
                onClick={() => setSelectedId(sale.id)}
              >
                <Table.Td>{sale.id}</Table.Td>
                <Table.Td>{new Date(sale.created_at).toLocaleString()}</Table.Td>
                <Table.Td>{sale.customer_name ?? "—"}</Table.Td>
                <Table.Td>{sale.item_count}</Table.Td>
                <Table.Td>{sale.total.toFixed(2)}</Table.Td>
                <Table.Td>
                  <Badge color={sale.payment_status === "paid" ? "green" : "red"} size="sm">
                    {sale.payment_status}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      {/* Receipt Modal */}
      <Modal
        opened={selectedId !== null}
        onClose={() => setSelectedId(null)}
        title={`Receipt #${selectedId}`}
        size="md"
      >
        {receiptIsError ? (
          <Text c="red" size="sm">Failed to load receipt. Please try again.</Text>
        ) : receipt ? (
          <Stack gap="sm">
            <ReceiptView receipt={receipt} />
            <Button fullWidth mt="sm" onClick={() => setSelectedId(null)}>
              Close
            </Button>
          </Stack>
        ) : (
          <Text c="dimmed" size="sm">Loading receipt…</Text>
        )}
      </Modal>
    </Box>
  );
}
