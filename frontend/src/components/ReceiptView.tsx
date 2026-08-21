import {
  Stack,
  Group,
  Text,
  Table,
  Divider,
  Badge,
  Title,
  Button,
} from "@mantine/core";
import type { Receipt } from "../api/client";

export default function ReceiptView({ receipt }: { receipt: Receipt }) {
  return (
    <div className="receipt-printable">
      <Stack gap="sm">
        <Title order={4} ta="center">Santé</Title>

        <Group justify="space-between">
          <Text size="sm" c="dimmed">Date</Text>
          <Text size="sm">{new Date(receipt.created_at).toLocaleString()}</Text>
        </Group>
        <Group justify="space-between">
          <Text size="sm" c="dimmed">Customer</Text>
          <Text size="sm">{receipt.customer_name ?? "Walk-in"}</Text>
        </Group>

        <Divider />

        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Product</Table.Th>
              <Table.Th>Qty</Table.Th>
              <Table.Th>Unit price</Table.Th>
              <Table.Th>Total</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {receipt.items.map((item, i) => (
              <Table.Tr key={i}>
                <Table.Td>{item.product_name}</Table.Td>
                <Table.Td>{item.qty}</Table.Td>
                <Table.Td>{item.unit_price.toFixed(2)}</Table.Td>
                <Table.Td>{item.line_total.toFixed(2)}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>

        <Divider />

        <Group justify="space-between">
          <Text size="sm" c="dimmed">Subtotal</Text>
          <Text size="sm">{receipt.subtotal.toFixed(2)}</Text>
        </Group>
        {receipt.discount_pct > 0 && (
          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              Discount ({receipt.discount_pct}%)
            </Text>
            <Text size="sm" c="red">
              -{receipt.discount_amount.toFixed(2)}
            </Text>
          </Group>
        )}
        <Group justify="space-between">
          <Text fw={700}>TOTAL</Text>
          <Text fw={700}>{receipt.total.toFixed(2)}</Text>
        </Group>

        <Group justify="center" mt="xs">
          <Badge
            color={receipt.payment_status === "paid" ? "green" : "orange"}
            size="lg"
          >
            {receipt.payment_status === "paid" ? "PAID" : "UNPAID"}
          </Badge>
        </Group>

        <Button
          fullWidth
          variant="light"
          mt="sm"
          className="no-print"
          onClick={() => window.print()}
        >
          Print / Save PDF
        </Button>
      </Stack>
    </div>
  );
}
