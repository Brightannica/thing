#include <Arduino.h>
#include <EEPROM.h>

#define EEPROM_SIZE 1024
#define MAX_COMPRESSED_SIZE 64

// Message types
#define TYPE_QUESTION 'Q'
#define TYPE_RESPONSE 'A'

unsigned long lastStatsSent = 0;

// Function declarations (to fix "not declared in scope" errors)
void blinkLED(int times);
void storeMessage(String message, char type);
void sendChatHistory();
void sendDetailedStats();
int getFreeMemory();
int findFreeAddress();
void clearChat();

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  
  while (!Serial) {
    delay(10);
  }
  
  Serial.println("READY:AI_Assistant_Core");
  blinkLED(3);
}

void loop() {
  // Handle serial commands
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.startsWith("STORE_Q:")) {
      storeMessage(command.substring(8), TYPE_QUESTION);
      Serial.println("STORED_Q");
    }
    else if (command.startsWith("STORE_A:")) {
      storeMessage(command.substring(8), TYPE_RESPONSE);
      Serial.println("STORED_A");
    }
    else if (command == "GET_CHAT") {
      sendChatHistory();
    }
    else if (command == "CLEAR_CHAT") {
      clearChat();
      Serial.println("CHAT_CLEARED");
    }
    else if (command == "GET_STATS") {
      sendDetailedStats();
    }
    else if (command == "LED_ON") {
      digitalWrite(LED_BUILTIN, HIGH);
      Serial.println("LED_ON");
    }
    else if (command == "LED_OFF") {
      digitalWrite(LED_BUILTIN, LOW);
      Serial.println("LED_OFF");
    }
  }
  
  // Auto-send stats every 5 seconds
  if (millis() - lastStatsSent > 5000) {
    sendDetailedStats();
    lastStatsSent = millis();
  }
}

void storeMessage(String message, char type) {
  int addr = findFreeAddress();
  if (addr == -1) {
    Serial.println("STORAGE_FULL");
    return;
  }
  
  // Simple storage: type + length + message
  EEPROM.write(addr, type);
  EEPROM.write(addr + 1, message.length());
  
  for (int i = 0; i < message.length() && i < MAX_COMPRESSED_SIZE; i++) {
    EEPROM.write(addr + 2 + i, message[i]);
  }
}

void sendChatHistory() {
  Serial.println("CHAT_HISTORY_START");
  
  for (int addr = 0; addr < EEPROM_SIZE; ) {
    char type = EEPROM.read(addr);
    if (type == 0xFF) break;
    
    int length = EEPROM.read(addr + 1);
    Serial.print("ENTRY:");
    Serial.print(type);
    Serial.print(":");
    
    for (int i = 0; i < length; i++) {
      char c = EEPROM.read(addr + 2 + i);
      if (c == 0xFF) break;
      Serial.print(c);
    }
    Serial.println();
    
    addr += 2 + length;
  }
  
  Serial.println("CHAT_HISTORY_END");
}

void sendDetailedStats() {
  int used = 0;
  int entries = 0;
  int freeMemory = getFreeMemory();
  
  for (int addr = 0; addr < EEPROM_SIZE; ) {
    char type = EEPROM.read(addr);
    if (type == 0xFF) break;
    
    int length = EEPROM.read(addr + 1);
    used += 2 + length;
    entries++;
    addr += 2 + length;
  }
  
  float usagePercent = (float)used / EEPROM_SIZE * 100;
  
  Serial.print("STATS:RAM=");
  Serial.print(freeMemory);
  Serial.print(",EEPROM_USED=");
  Serial.print(used);
  Serial.print(",EEPROM_TOTAL=");
  Serial.print(EEPROM_SIZE);
  Serial.print(",USAGE=");
  Serial.print(usagePercent);
  Serial.print("%,ENTRIES=");
  Serial.print(entries);
  Serial.print(",UPTIME=");
  Serial.print(millis() / 1000);
  Serial.println("s");
}

int getFreeMemory() {
  extern int __heap_start, *__brkval;
  int v;
  return (int) &v - (__brkval == 0 ? (int) &__heap_start : (int) __brkval);
}

int findFreeAddress() {
  for (int addr = 0; addr < EEPROM_SIZE; ) {
    char type = EEPROM.read(addr);
    if (type == 0xFF) return addr;
    
    int length = EEPROM.read(addr + 1);
    addr += 2 + length;
    
    if (addr >= EEPROM_SIZE) return -1;
  }
  return 0;
}

void clearChat() {
  for (int i = 0; i < EEPROM_SIZE; i++) {
    EEPROM.write(i, 0xFF);
  }
}

void blinkLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(150);
    digitalWrite(LED_BUILTIN, LOW);
    delay(150);
  }
}
