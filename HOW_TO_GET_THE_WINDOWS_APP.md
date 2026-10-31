# How to get your Windows installer (no coding needed)

The installer can only be built on a Windows computer. GitHub gives you one for free, and builds it automatically.

1. Create a free account at https://github.com (sign up).
2. Click the **+** at the top right, then **New repository**. Name it `AimLabPro`, choose **Private**, click **Create repository**.
3. On the new page click **uploading an existing file**. Unzip `AimLabPro-source.zip` on your PC, then drag the *contents* of the unzipped folder into the browser (including the hidden `.github` folder; if your drag-and-drop skips it, tell me and I'll give you another way). Click **Commit changes**.
4. Click the **Actions** tab. A job called **Build Windows installer** starts by itself (takes about 5-10 minutes). Wait for the green tick.
5. Click the finished job, scroll to **Artifacts**, download **AimLabPro-Windows-Installer**, unzip it, and run `AimLabPro-Setup-0.1.0.exe`.
   (Or download **AimLabPro-Portable** and run `AimLabPro.exe` inside without installing.)

If the job shows a red X, click it, copy the error text and send it to me. I will fix it.
