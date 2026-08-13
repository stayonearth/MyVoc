-- MyVoc 数据库恢复脚本
-- 生成时间: 2026-08-13
-- 包含 84 个单词、66 条学习记录、2 个会话

-- 删除现有表（如果存在），避免冲突
DROP TABLE IF EXISTS learning_records;
DROP TABLE IF EXISTS daily_sessions;
DROP TABLE IF EXISTS words;
DROP TABLE IF EXISTS sqlite_sequence;

BEGIN TRANSACTION;
CREATE TABLE daily_sessions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date DATE    UNIQUE NOT NULL,
            word_ids     TEXT    DEFAULT '[]',
            total_words  INTEGER DEFAULT 0
        );
INSERT INTO "daily_sessions" VALUES(2,'2026-08-12','[1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67]',66);
INSERT INTO "daily_sessions" VALUES(3,'2026-08-13','[68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86]',19);
CREATE TABLE learning_records (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id          INTEGER NOT NULL REFERENCES words(id),
            learn_date       DATE    NOT NULL,
            stage            INTEGER DEFAULT 0,
            ease_factor      REAL    DEFAULT 2.5,
            interval         INTEGER DEFAULT 0,
            next_review_date DATE,
            correct_count    INTEGER DEFAULT 0,
            wrong_count      INTEGER DEFAULT 0,
            last_result      TEXT,
            last_review_at   DATETIME
        );
INSERT INTO "learning_records" VALUES(2,4,'2026-08-12',0,2.3,1,'2026-08-13',2,1,'wrong','2026-08-12 13:25:25');
INSERT INTO "learning_records" VALUES(3,1,'2026-08-12',6,2.5,30,'2026-09-11',6,0,'correct','2026-08-12 14:00:56');
INSERT INTO "learning_records" VALUES(4,2,'2026-08-12',1,1.89999999999999964472e+00,1,'2026-08-13',3,3,'correct','2026-08-12 14:00:59');
INSERT INTO "learning_records" VALUES(6,5,'2026-08-12',3,2.5,4,'2026-08-16',3,0,'correct','2026-08-12 14:01:11');
INSERT INTO "learning_records" VALUES(7,6,'2026-08-12',3,2.5,4,'2026-08-16',3,0,'correct','2026-08-12 14:01:17');
INSERT INTO "learning_records" VALUES(8,7,'2026-08-12',2,2.5,2,'2026-08-14',2,0,'correct','2026-08-12 14:01:22');
INSERT INTO "learning_records" VALUES(9,8,'2026-08-12',2,2.5,2,'2026-08-14',2,0,'correct','2026-08-12 14:01:53');
INSERT INTO "learning_records" VALUES(10,9,'2026-08-12',2,2.5,2,'2026-08-14',2,0,'correct','2026-08-12 14:01:56');
INSERT INTO "learning_records" VALUES(11,10,'2026-08-12',2,2.5,2,'2026-08-14',2,0,'correct','2026-08-12 14:01:59');
INSERT INTO "learning_records" VALUES(12,11,'2026-08-12',0,1.69999999999999973354e+00,1,'2026-08-13',0,4,'wrong','2026-08-12 14:02:04');
INSERT INTO "learning_records" VALUES(13,12,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:02:21');
INSERT INTO "learning_records" VALUES(14,13,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:03:11');
INSERT INTO "learning_records" VALUES(15,14,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:03:17');
INSERT INTO "learning_records" VALUES(16,15,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:03:22');
INSERT INTO "learning_records" VALUES(17,16,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:03:39');
INSERT INTO "learning_records" VALUES(18,17,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:03:48');
INSERT INTO "learning_records" VALUES(19,18,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:03:52');
INSERT INTO "learning_records" VALUES(20,19,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:04:07');
INSERT INTO "learning_records" VALUES(21,20,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:04:14');
INSERT INTO "learning_records" VALUES(22,21,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:04:23');
INSERT INTO "learning_records" VALUES(23,22,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:04:27');
INSERT INTO "learning_records" VALUES(24,23,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:04:33');
INSERT INTO "learning_records" VALUES(25,24,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:04:43');
INSERT INTO "learning_records" VALUES(26,25,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:04:49');
INSERT INTO "learning_records" VALUES(27,26,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:04:57');
INSERT INTO "learning_records" VALUES(28,27,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:05:00');
INSERT INTO "learning_records" VALUES(29,28,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:05:11');
INSERT INTO "learning_records" VALUES(30,29,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:05:14');
INSERT INTO "learning_records" VALUES(31,30,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:05:25');
INSERT INTO "learning_records" VALUES(32,31,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:05:43');
INSERT INTO "learning_records" VALUES(33,32,'2026-08-12',0,2.3,1,'2026-08-13',0,1,'wrong','2026-08-12 14:05:59');
INSERT INTO "learning_records" VALUES(34,33,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:06:02');
INSERT INTO "learning_records" VALUES(35,34,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:06:07');
INSERT INTO "learning_records" VALUES(36,35,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:06:15');
INSERT INTO "learning_records" VALUES(37,36,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:06:21');
INSERT INTO "learning_records" VALUES(38,37,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:06:33');
INSERT INTO "learning_records" VALUES(39,38,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:06:39');
INSERT INTO "learning_records" VALUES(40,39,'2026-08-12',0,2.3,1,'2026-08-13',0,1,'wrong','2026-08-12 14:06:50');
INSERT INTO "learning_records" VALUES(41,40,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:06:56');
INSERT INTO "learning_records" VALUES(42,41,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:07:02');
INSERT INTO "learning_records" VALUES(43,42,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:07:22');
INSERT INTO "learning_records" VALUES(44,43,'2026-08-12',0,2.3,1,'2026-08-13',0,1,'wrong','2026-08-12 14:07:27');
INSERT INTO "learning_records" VALUES(45,44,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:07:43');
INSERT INTO "learning_records" VALUES(46,45,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:07:46');
INSERT INTO "learning_records" VALUES(47,46,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:07:50');
INSERT INTO "learning_records" VALUES(48,47,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:07:54');
INSERT INTO "learning_records" VALUES(49,48,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:08:00');
INSERT INTO "learning_records" VALUES(51,50,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:08:14');
INSERT INTO "learning_records" VALUES(52,51,'2026-08-12',0,2.3,1,'2026-08-13',0,1,'wrong','2026-08-12 14:08:26');
INSERT INTO "learning_records" VALUES(53,52,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:08:41');
INSERT INTO "learning_records" VALUES(54,53,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:08:46');
INSERT INTO "learning_records" VALUES(55,54,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:09:08');
INSERT INTO "learning_records" VALUES(56,55,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:09:11');
INSERT INTO "learning_records" VALUES(57,56,'2026-08-12',0,2.3,1,'2026-08-13',0,1,'wrong','2026-08-12 14:09:28');
INSERT INTO "learning_records" VALUES(58,57,'2026-08-12',0,2.3,1,'2026-08-13',0,1,'wrong','2026-08-12 14:09:32');
INSERT INTO "learning_records" VALUES(59,58,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:09:42');
INSERT INTO "learning_records" VALUES(60,59,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:09:45');
INSERT INTO "learning_records" VALUES(61,60,'2026-08-12',0,2.3,1,'2026-08-13',0,1,'wrong','2026-08-12 14:09:50');
INSERT INTO "learning_records" VALUES(62,61,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:10:02');
INSERT INTO "learning_records" VALUES(63,62,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:10:24');
INSERT INTO "learning_records" VALUES(64,63,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:10:29');
INSERT INTO "learning_records" VALUES(65,64,'2026-08-12',0,2.3,1,'2026-08-13',0,1,'wrong','2026-08-12 14:10:33');
INSERT INTO "learning_records" VALUES(66,65,'2026-08-12',1,2.5,1,'2026-08-13',1,0,'correct','2026-08-12 14:10:38');
INSERT INTO "learning_records" VALUES(67,66,'2026-08-12',0,2.3,1,'2026-08-13',0,1,'wrong','2026-08-12 14:10:46');
INSERT INTO "learning_records" VALUES(68,67,'2026-08-12',0,2.3,1,'2026-08-13',0,1,'wrong','2026-08-12 14:11:08');
INSERT INTO "learning_records" VALUES(69,68,'2026-08-13',1,2.5,1,'2026-08-14',1,0,'correct','2026-08-13 06:46:15');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('words',86);
INSERT INTO "sqlite_sequence" VALUES('daily_sessions',3);
INSERT INTO "sqlite_sequence" VALUES('learning_records',69);
CREATE TABLE words (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            word       TEXT    UNIQUE NOT NULL,
            phonetic   TEXT    DEFAULT '',
            meaning    TEXT    DEFAULT '',
            created_at DATETIME DEFAULT (datetime('now')),
            source     TEXT    DEFAULT 'api'
        , audio_url TEXT DEFAULT '');
INSERT INTO "words" VALUES(1,'abandon','','v. 放弃，抛弃','2026-08-12 13:23:17','api','');
INSERT INTO "words" VALUES(2,'ability','','n. 能力，才能','2026-08-12 13:25:04','api','');
INSERT INTO "words" VALUES(4,'test','v. 测试','api','2026-08-12 13:25:25','api','');
INSERT INTO "words" VALUES(5,'create','','v. 创造，创建；设计，创作；造成，引起；授予，册封；<英，非正式>大惊小怪，抱怨','2026-08-12 13:31:14','api','');
INSERT INTO "words" VALUES(6,'creative','','adj. 创造（性）的，创作的；有创造力的，有想象力的; n. 创作者；创意，创作素材','2026-08-12 13:35:52','api','');
INSERT INTO "words" VALUES(7,'creature','','n. 生物，动物；（具有某种特征的）人；怪物；受支配的人，产物','2026-08-12 13:36:23','api','');
INSERT INTO "words" VALUES(8,'credit','','n. 信用，信贷，赊购；赞扬，信誉，声望；存款金额，余额；补助；退税，抵免；学分；带来荣耀的人（或事...','2026-08-12 13:39:23','api','');
INSERT INTO "words" VALUES(9,'crew','','n. 全体船员，全体机组人员；一组工作人员；一伙人，一帮人；全体划船队员；赛艇运动；<美，非正式>（...','2026-08-12 13:39:31','api','');
INSERT INTO "words" VALUES(10,'crime','','n. 罪，罪行；犯罪，犯罪活动；可耻行为，错误; v. <英，非正式>（尤指在军队里）指控……有罪，...','2026-08-12 13:39:42','api','');
INSERT INTO "words" VALUES(11,'criminial','','n. 罪犯; adj. 犯法的，犯罪的；刑事的；应受责备的，可耻的；罪犯的，犯人的；<非正式>（行为...','2026-08-12 13:39:50','api','');
INSERT INTO "words" VALUES(12,'crisis','','n. 危机，紧要关头；决定性时刻，关键时刻；（病情的）转折点，危象; adj. 用于处理危机的','2026-08-12 13:39:56','api','');
INSERT INTO "words" VALUES(13,'criterion','','n. 尺度，标准，准则','2026-08-12 13:40:03','api','');
INSERT INTO "words" VALUES(14,'critic','','n. 批评家，评论员；批评者，反对……的人','2026-08-12 13:40:08','api','');
INSERT INTO "words" VALUES(15,'critical','','adj. 批判的，爱挑剔的；极其重要的，关键的；严重的，危急的；病重的，重伤的；评论性的，评论家的；...','2026-08-12 13:40:15','api','');
INSERT INTO "words" VALUES(16,'criticism','','n. 批评，批判；意见；评论，评价；（对文学作品和历史文献的）考证','2026-08-12 13:40:20','api','');
INSERT INTO "words" VALUES(17,'criticise','','vt. 批评；评论；评判（criticize 的英式拼写）; vi. 批评；评论（criticize...','2026-08-12 13:40:31','api','');
INSERT INTO "words" VALUES(18,'crop','','n. 庄稼；（谷物或水果的）收成，产量；（同时涌现的）一批，一帮；平头，短发；（尤指头发）大量，丰富...','2026-08-12 13:40:56','api','');
INSERT INTO "words" VALUES(19,'cross','','v. 反对；杂交；在（支票）上划线（表示只能转入银行帐户）；超过，超出（极限或范围）；（表情）掠过，...','2026-08-12 13:41:03','api','');
INSERT INTO "words" VALUES(20,'crossroads','','n. 十字路口；交叉路口；聚会的中心地点','2026-08-12 13:41:09','api','');
INSERT INTO "words" VALUES(21,'crowd','','n. 人群；一伙人；百姓，凡夫俗子；（尤指体育运动赛事的）观众，听众; v. 聚集，群集；靠近，盯着...','2026-08-12 13:41:14','api','');
INSERT INTO "words" VALUES(22,'crowded','','adj. 拥挤的，塞满的; v. 聚集，群集；挤满，塞满；靠近，盯着（crowd 的过去式和过去分词...','2026-08-12 13:41:22','api','');
INSERT INTO "words" VALUES(23,'crown','','n. 王冠，冕；王位，王权（the crown）；王国政府，王国（the Crown）；冠军宝座，桂...','2026-08-12 13:41:26','api','');
INSERT INTO "words" VALUES(24,'crucial','','adj. 至关重要的，决定性的；<非正式>极好的','2026-08-12 13:41:38','api','');
INSERT INTO "words" VALUES(25,'cruel','','adj. 残酷的，残忍的；引起痛苦的; v. <非正式>弄糟，使没有成功可能','2026-08-12 13:41:43','api','');
INSERT INTO "words" VALUES(26,'cruelty','','n. 残酷，残忍；不公，虐待','2026-08-12 13:41:48','api','');
INSERT INTO "words" VALUES(27,'cry','','v. 哭，哭泣；喊叫，呼喊；（兽或鸟）大叫; n. （表达强烈感情的）叫喊，叫声，哭声；大喊，大叫；...','2026-08-12 13:41:53','api','');
INSERT INTO "words" VALUES(28,'crystal','','n. 结晶，晶体；水晶；水晶玻璃；（钟表的）石英玻璃保护面，表蒙子; adj. 晶莹的，清澈透明的;...','2026-08-12 13:41:58','api','');
INSERT INTO "words" VALUES(29,'cucumber','','n. 黄瓜；胡瓜','2026-08-12 13:42:05','api','');
INSERT INTO "words" VALUES(30,'cuisine','','n. 烹饪，风味；饭菜，菜肴; 【名】 （Cuisine）（法）屈西纳（人名）','2026-08-12 13:54:52','api','');
INSERT INTO "words" VALUES(31,'cultivate','','v. 开垦，耕作；栽培，培育；陶冶，培养；建立（友谊），结交','2026-08-12 13:55:05','api','');
INSERT INTO "words" VALUES(32,'culture','','n. 文化，文明；（团体或组织中共同的）态度，习俗；文化群落，（处于历史上特定时期的）社会；艺术活动...','2026-08-12 13:55:09','api','');
INSERT INTO "words" VALUES(33,'cup','','n. 杯子；一杯（的量）；杯（烹饪的计量单位），量杯（金属或塑料量器）；优胜杯，奖杯；杯状物；（胸罩...','2026-08-12 13:55:14','api','');
INSERT INTO "words" VALUES(34,'cupboard','','n. 橱柜，衣柜；壁橱；小储藏室','2026-08-12 13:55:24','api','');
INSERT INTO "words" VALUES(35,'cure','','n. 药物，疗法；对策，措施；治愈，治疗；（对橡胶、塑料或其他材料的）熟化；（基督教牧师的）牧师责任...','2026-08-12 13:55:29','api','');
INSERT INTO "words" VALUES(36,'curious','','adj. 好奇的，求知欲强的；稀奇的，不寻常的；爱挑剔的','2026-08-12 13:55:34','api','');
INSERT INTO "words" VALUES(37,'currency','','n. 通货，货币；通用，流行；现时性','2026-08-12 13:55:44','api','');
INSERT INTO "words" VALUES(38,'current','','adj. 现行的，当前的；通用的，流行的；最近的; n. 水流，气流；电流；思潮，趋势; 【名】 （...','2026-08-12 13:55:50','api','');
INSERT INTO "words" VALUES(39,'curriculum','','n. 课程','2026-08-12 13:55:57','api','');
INSERT INTO "words" VALUES(40,'curtain','','n. 窗帘，门帘；帘状物，幕状物（如浓烟或大雨等）；纱幔，帷幔；（舞台上的）幕，幕布；开幕，落幕；灾...','2026-08-12 13:56:02','api','');
INSERT INTO "words" VALUES(41,'curve','','n. 曲线，弧线；转弯，弯道；图表曲线；曲线球；（女子身体的）曲线; v. （使）弯曲，（使）呈曲线...','2026-08-12 13:56:07','api','');
INSERT INTO "words" VALUES(42,'cushion','','n. 垫子，坐垫；减震垫，缓冲垫；起缓解作用的东西；大比分领先，稳操胜券；（台球桌的）弹性衬边; v...','2026-08-12 13:56:12','api','');
INSERT INTO "words" VALUES(43,'custom','','n. 风俗，习俗；习惯；光顾，惠顾；<法律>惯例，习惯法；（经常性的）顾客; adj. 定做的，量身...','2026-08-12 13:56:17','api','');
INSERT INTO "words" VALUES(44,'customer','','n. 顾客；（某一类型的）家伙','2026-08-12 13:56:23','api','');
INSERT INTO "words" VALUES(45,'cut','','v. 切，割，剪；削减，缩减；删节，删减；停止，切断；抄近路，穿过；切（牌），倒（牌）；灌制（唱片）...','2026-08-12 13:56:28','api','');
INSERT INTO "words" VALUES(46,'cute','','adj. 漂亮的，可爱的；<美>性感迷人的；<美>精明的，机灵的；<美，非正式>矫揉造作的','2026-08-12 13:56:33','api','');
INSERT INTO "words" VALUES(47,'cycle','','n. 自行车，摩托车；循环，周期；组诗，组歌；整套，系列；自行车骑行；一段时间; v. 骑自行车；循...','2026-08-12 13:56:38','api','');
INSERT INTO "words" VALUES(48,'cyclist','','n. 骑自行车的人','2026-08-12 13:56:46','api','');
INSERT INTO "words" VALUES(50,'daily','','adj. 每日的，日常的；一天的，按天计算的; adv. 每日，每天；日常地; n. 日报；<英>日...','2026-08-12 13:57:09','api','');
INSERT INTO "words" VALUES(51,'dairy','','adj. 奶制的，乳品的；乳品业的，生产乳品的; n. 乳品公司，乳品店；乳制品；牛奶场，乳品场；<...','2026-08-12 13:57:14','api','');
INSERT INTO "words" VALUES(52,'dam','','n. 堤，坝；母兽，母畜；<南非>水库；（牙科手术中的）橡皮障; v. （在河上）筑坝；阻止，抑制;...','2026-08-12 13:57:19','api','');
INSERT INTO "words" VALUES(53,'damage','','n. （有形的）损坏，损失；损害，伤害；损害赔偿金；费用，代价; v. 损坏，损害；对……造成坏影响','2026-08-12 13:57:24','api','');
INSERT INTO "words" VALUES(54,'damp','','adj. 潮湿的; n. 湿气，潮气；沼气；气馁; v. 使潮湿，弄湿；减弱，抑制；把（火）调小；限...','2026-08-12 13:57:35','api','');
INSERT INTO "words" VALUES(55,'dance','','v. 跳舞；跳（某种舞）；跳跃，雀跃；和……共舞；（某物）摆动，摇晃；（某人眼睛）因快乐（或激动）而...','2026-08-12 13:57:40','api','');
INSERT INTO "words" VALUES(56,'danager','','血液琼脂培养基','2026-08-12 13:57:45','api','');
INSERT INTO "words" VALUES(57,'danagerous','','adj. 危险的，有威胁的','2026-08-12 13:57:50','api','');
INSERT INTO "words" VALUES(58,'dare','','v. 激，激将；敢于，胆敢; n. 挑战，激将; 【名】 （Dare）（美）达雷（人名）','2026-08-12 13:57:56','api','');
INSERT INTO "words" VALUES(59,'dark','','adj. 黑暗的，昏暗的；深色的，暗色的；恐怖的，悲惨的；神秘的，隐秘的；忧郁的，悲观的；邪恶的，阴...','2026-08-12 13:58:01','api','');
INSERT INTO "words" VALUES(60,'darling','','n. 亲爱的，宝贝；亲切友好的人；宠儿，红人; adj. 亲爱的，心爱的；可爱的，迷人的; 【名】 ...','2026-08-12 13:58:06','api','');
INSERT INTO "words" VALUES(61,'dash','','v. 猛冲，急奔；猛撞，撞击；使（希望或期望）破灭；迅速写或画; n. 猛冲，飞奔；少量，少许（添加...','2026-08-12 13:58:11','api','');
INSERT INTO "words" VALUES(62,'database','','n. （计算机）数据库，资料库','2026-08-12 13:58:16','api','');
INSERT INTO "words" VALUES(63,'date','','n. 日期，日子；约会，幽会；约会对象；椰枣，海枣; v. 注明日期；确定年代；<美>谈恋爱，约会；...','2026-08-12 13:58:20','api','');
INSERT INTO "words" VALUES(64,'datum','','n. 数据，资料；前提，假定；基准点','2026-08-12 13:58:25','api','');
INSERT INTO "words" VALUES(65,'daughter','','n. 女儿；[遗][农学] 子代; adj. 女儿的；子代的','2026-08-12 13:58:30','api','');
INSERT INTO "words" VALUES(66,'dawn','','v. 变得明朗，开始清楚；破晓，开始; n. 拂晓，黎明；曙光，开端; 【名】 （Dawn）（西）道...','2026-08-12 13:58:35','api','');
INSERT INTO "words" VALUES(67,'day','','n. 一天；白昼，白天；工作日，一天的活动时间；时期，时代；如今，现在；（过去或将来的）一天；重大日...','2026-08-12 13:58:41','api','');
INSERT INTO "words" VALUES(68,'daylight','','n. 白天，日光；黎明，拂晓；差距，差别','2026-08-13 04:07:11','api','');
INSERT INTO "words" VALUES(69,'daytime','','n. 白天; adj. 日间的','2026-08-13 04:07:19','api','');
INSERT INTO "words" VALUES(70,'dead','','adj. 死的，去世的；不再使用的，用尽的；（因无电力）不工作的；无生气的，死气沉沉的；过时的，不再...','2026-08-13 04:07:25','api','');
INSERT INTO "words" VALUES(71,'deadline','','n. 最后期限，截止日期；<史>（监狱周围的）死线','2026-08-13 04:51:18','api','');
INSERT INTO "words" VALUES(72,'deaf','','adj. 聋的；置若罔闻的','2026-08-13 04:51:23','api','');
INSERT INTO "words" VALUES(73,'deal','','n. 大量；交易；坏运气，不公平的对待；发牌；冷衫木；优惠的价格，划算的价格；牌戏的一局；一手牌; ...','2026-08-13 04:51:27','api','');
INSERT INTO "words" VALUES(74,'dear','','adj. 珍视的；(用于信函抬头名字或头衔前)亲爱的；昂贵的; n. （称呼所爱的人）亲爱的; in...','2026-08-13 04:51:33','api','');
INSERT INTO "words" VALUES(75,'death','','n. 死，死亡；破灭，终止；死神','2026-08-13 04:51:37','api','');
INSERT INTO "words" VALUES(76,'debate','','n. 讨论，辩论; v. 反复思考，斟酌；讨论，辩论','2026-08-13 04:51:42','api','');
INSERT INTO "words" VALUES(77,'debt','','n. 欠款，债务；负债情况；人情债','2026-08-13 04:51:47','api','');
INSERT INTO "words" VALUES(78,'decade','','n. 十年，十年期；十进','2026-08-13 04:51:51','api','');
INSERT INTO "words" VALUES(79,'decay','','v. （建筑、地方等）破败，衰落；（观念、影响力等）衰败；（使）腐朽，腐烂; n. 腐烂；（观念、机...','2026-08-13 04:51:54','api','');
INSERT INTO "words" VALUES(80,'deceive','','v. 欺骗，蒙骗；使误信，误导；对（丈夫、妻子或伴侣）不忠','2026-08-13 04:52:05','api','');
INSERT INTO "words" VALUES(81,'decent','','adj. 正派的；体面的，正经的；像样的；衣着得体的','2026-08-13 04:52:09','api','');
INSERT INTO "words" VALUES(82,'decide','','v. 影响（或决定）……的结果；断定，判定；使下决心；决定，选定；裁决，判决','2026-08-13 04:52:14','api','');
INSERT INTO "words" VALUES(83,'decision','','n. 决定，抉择；判决，裁定；果断，决断力；作决定，决策','2026-08-13 04:52:34','api','');
INSERT INTO "words" VALUES(84,'deck','','n. 甲板，舱面；（船或公共汽车的）层；<美>一副牌；（屋后供休息的）木制平台；（唱机的）盘装置，（...','2026-08-13 04:52:38','api','');
INSERT INTO "words" VALUES(85,'declare','','v. 宣布，声明；断言，宣称；申报；放弃击球，宣布结束赛局','2026-08-13 04:52:44','api','');
INSERT INTO "words" VALUES(86,'decline','','v. 下降，衰退；拒绝，谢绝；变格，词形变化; n. 减少，衰退','2026-08-13 04:52:53','api','');
COMMIT;