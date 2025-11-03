Python ASTM Protocol With MySql

Install Dependencies:

    `python -m pip install fastapi uvicorn pyserial mysql-connector-python pydantic`

To Run

1 Normal ASTM Data only

    `python astm_service.py`

2 ASTM Data with Patients Details

    `python astm_service_patientdetails.py`

For Series

🧩 1️⃣ Physically connect the hardware

Plug the Atellica cable (usually USB or RS232-to-USB) into your PC.

Wait 5–10 seconds — Windows should automatically detect it.

You’ll usually hear the “device connected” sound.


🧭 2️⃣ Verify the connection

Open Device Manager → Ports (COM & LPT)

You should now see something like:

USB Serial Device (COM4)


or

Siemens Atellica Data Interface (COM6)


That confirms Windows recognized the hardware and created a COM port for it.

⚙️ 3️⃣ Note the COM port number

Write down the port number (example: COM4).

That’s what the Python code must use.


🧠 4️⃣ Update and run the code

In your Python script, find this section:

COM_PORT = "COM4"  # change this to your real port
BAUD_RATE = 9600   # or 115200, depending on analyzer config
ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)


Then run the script.
If everything’s correct, you’ll see:

[info] Connected to COM4 at 9600 baud
[ready] Waiting for ASTM frames...


When the analyzer sends data, the listener will:

Print the parsed ASTM message in console.

Save patient + result details in your MySQL database.

If you connect the device but no COM port appears, it means:

The correct driver for the USB adapter isn’t installed yet.

You may need the manufacturer’s USB-to-serial driver (CP210x, FTDI, or Prolific).
