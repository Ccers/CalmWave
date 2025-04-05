-- MySQL dump 10.13  Distrib 8.0.38, for Win64 (x86_64)
--
-- Host: localhost    Database: calmwave_databases
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `bluetooth_device`
--

DROP TABLE IF EXISTS `bluetooth_device`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bluetooth_device` (
  `device_id` int NOT NULL AUTO_INCREMENT,
  `device_name` varchar(100) NOT NULL,
  `mac_address` varchar(17) NOT NULL,
  `last_connected_time` datetime DEFAULT NULL,
  PRIMARY KEY (`device_id`),
  UNIQUE KEY `mac_address` (`mac_address`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bluetooth_device`
--

LOCK TABLES `bluetooth_device` WRITE;
/*!40000 ALTER TABLE `bluetooth_device` DISABLE KEYS */;
INSERT INTO `bluetooth_device` VALUES (1,'1','123455','2025-04-05 12:27:12');
/*!40000 ALTER TABLE `bluetooth_device` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `device_connection_history`
--

DROP TABLE IF EXISTS `device_connection_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `device_connection_history` (
  `history_id` int NOT NULL AUTO_INCREMENT,
  `account` varchar(50) NOT NULL,
  `device_id` int NOT NULL,
  `connection_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `disconnection_time` datetime DEFAULT NULL,
  `connection_status` enum('已连接','已断开') NOT NULL,
  PRIMARY KEY (`history_id`),
  KEY `device_connection_history_ibfk_1` (`account`),
  KEY `device_connection_history_ibfk_2` (`device_id`),
  CONSTRAINT `device_connection_history_ibfk_1` FOREIGN KEY (`account`) REFERENCES `user` (`account`),
  CONSTRAINT `device_connection_history_ibfk_2` FOREIGN KEY (`device_id`) REFERENCES `bluetooth_device` (`device_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `device_connection_history`
--

LOCK TABLES `device_connection_history` WRITE;
/*!40000 ALTER TABLE `device_connection_history` DISABLE KEYS */;
INSERT INTO `device_connection_history` VALUES (1,'123',1,'2025-04-05 12:32:10',NULL,'已连接');
/*!40000 ALTER TABLE `device_connection_history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `pressure_data`
--

DROP TABLE IF EXISTS `pressure_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pressure_data` (
  `id` int NOT NULL AUTO_INCREMENT,
  `account` varchar(50) NOT NULL,
  `pressure_value` decimal(5,2) NOT NULL,
  `record_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `device_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `pressure_data_ibfk_1` (`account`),
  KEY `pressure_data_ibfk_2` (`device_id`),
  CONSTRAINT `pressure_data_ibfk_1` FOREIGN KEY (`account`) REFERENCES `user` (`account`),
  CONSTRAINT `pressure_data_ibfk_2` FOREIGN KEY (`device_id`) REFERENCES `bluetooth_device` (`device_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pressure_data`
--

LOCK TABLES `pressure_data` WRITE;
/*!40000 ALTER TABLE `pressure_data` DISABLE KEYS */;
INSERT INTO `pressure_data` VALUES (1,'123',85.00,'2025-04-05 12:34:39',1),(2,'123',60.00,'2025-04-05 12:34:46',1),(3,'123',20.00,'2025-04-05 12:34:50',1),(4,'123',70.00,'2025-04-05 12:34:53',1),(5,'123',73.00,'2025-04-05 12:34:56',1);
/*!40000 ALTER TABLE `pressure_data` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `account` varchar(50) NOT NULL,
  `phone` varchar(20) NOT NULL,
  `password` varchar(255) DEFAULT NULL,
  `wechat_openid` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `account` (`account`),
  UNIQUE KEY `phone` (`phone`),
  UNIQUE KEY `wechat_openid` (`wechat_openid`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user`
--

LOCK TABLES `user` WRITE;
/*!40000 ALTER TABLE `user` DISABLE KEYS */;
INSERT INTO `user` VALUES (1,'12345','12345','12345',NULL,'12345','2025-04-01 09:15:16'),(2,'123465','123465','123465',NULL,'123465','2025-04-01 09:17:37'),(3,'123','123','123','$2b$12$4rbhCMPVJ3BShfCQ7ROBOuvuczwEXy0l75ERg5yWkFIXYYG92LEDe',NULL,'2025-04-04 05:58:36');
/*!40000 ALTER TABLE `user` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-04-05 14:38:03
