import { useState } from "react";
import {
  AppShell,
  Title,
  Text,
  Group,
  Button,
  NavLink,
  Box,
} from "@mantine/core";
import { useAuth } from "../auth/AuthContext";
import { NAV_ITEMS, ROLE_PERMISSIONS } from "../lib/roles";
import UsersPage from "../pages/UsersPage";

export default function AppLayout() {
  const { user, logout } = useAuth();

  const allowedKeys = user ? ROLE_PERMISSIONS[user.role] : [];
  const allowedItems = NAV_ITEMS.filter((item) => allowedKeys.includes(item.key));
  const defaultKey = allowedItems.length > 0 ? allowedItems[0].key : "";

  const [activeKey, setActiveKey] = useState(defaultKey);

  function renderContent() {
    const activeItem = allowedItems.find((i) => i.key === activeKey);
    if (!activeItem) return <Text c="dimmed">Nothing to show.</Text>;

    if (activeItem.key === "users") {
      return <UsersPage />;
    }

    return (
      <>
        <Title order={2}>{activeItem.label}</Title>
        <Text c="dimmed" mt="sm">
          Coming in a later phase.
        </Text>
      </>
    );
  }

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 200, breakpoint: "sm" }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Title order={3}>Santé</Title>
          <Group gap="sm">
            <Text size="sm" c="dimmed">
              {user?.username}
            </Text>
            <Button size="xs" variant="subtle" onClick={logout}>
              Logout
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        <Box>
          {allowedItems.map((item) => (
            <NavLink
              key={item.key}
              label={item.label}
              active={activeKey === item.key}
              onClick={() => setActiveKey(item.key)}
            />
          ))}
        </Box>
      </AppShell.Navbar>

      <AppShell.Main>
        {renderContent()}
      </AppShell.Main>
    </AppShell>
  );
}
