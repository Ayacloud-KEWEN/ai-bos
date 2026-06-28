import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';

import { TooltipProvider } from "@/components/ui/tooltip";
import { SidebarProvider, SidebarTrigger, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { LanguageSwitcher } from "@/components/language-switcher";
import "@xyflow/react/dist/style.css";
import { QueryProvider } from "@/components/providers/query-provider";
import { ActiveWorkspace } from "@/components/active-workspace";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI-BOS | Business Operating System",
  description: "Transform Company Intelligence into Business Execution.",
};

export default async function RootLayout({
  children,
  params
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}>) {
  const { locale } = await params;
  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={`${inter.className} antialiased`}>
        <NextIntlClientProvider messages={messages}>
          <QueryProvider>
            <TooltipProvider>
              <SidebarProvider>
                <AppSidebar />
                
                <SidebarInset>
                  <header className="flex h-14 items-center gap-4 border-b bg-background px-4 lg:h-[60px]">
                    <div className="flex flex-1 items-center gap-4">
                      <SidebarTrigger className="-ml-1" />
                      <div className="flex items-center gap-4 border-l pl-4 h-6">
                      <ActiveWorkspace />
                    </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <LanguageSwitcher />
                    </div>
                  </header>

                  <main className="flex-1 overflow-auto bg-muted/20">
                    {children}
                  </main>
                </SidebarInset>

              </SidebarProvider>
            </TooltipProvider>
          </QueryProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}