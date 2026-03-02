import "./globals.css";

export const metadata = {
  title: "Unity — Employee Evaluation Platform",
  description: "Monthly employee evaluation and voting platform for Unity",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
