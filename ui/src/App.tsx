/**
 * Provider nesting is firm (BLUEPRINT.md §3):
 * QueryClientProvider -> BrowserRouter -> ThemeProvider -> ToastProvider ->
 * <domain contexts go here> -> Routes under a single <Layout/>.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { ToastProvider } from "@/components/Toast";
import { AssistantProvider } from "@/lib/AssistantContext";
import { ThemeProvider } from "@/lib/ThemeContext";
import { Dashboard } from "@/pages/Dashboard";
import { ItemsPage } from "@/pages/Items";
import { ProfileDetailPage, ProfilesListPage } from "@/pages/Profiles";
import { UsersPage } from "@/pages/UsersPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5_000, refetchOnWindowFocus: true, retry: 1 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <ToastProvider>
            <AssistantProvider>
              <Routes>
                <Route element={<Layout />}>
                  <Route index element={<Dashboard />} />
                  <Route path="items" element={<ItemsPage />} />
                  <Route path="profiles" element={<ProfilesListPage />} />
                  <Route path="profiles/:profileId" element={<ProfileDetailPage />} />
                  <Route path="users" element={<UsersPage />} />
                </Route>
              </Routes>
            </AssistantProvider>
          </ToastProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
