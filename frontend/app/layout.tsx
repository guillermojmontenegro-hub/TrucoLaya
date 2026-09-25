import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = { title: "Truco Laya", description: "Truco argentino contra la IA Laya" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es"><body>{children}</body></html>;
}
