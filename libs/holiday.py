class ChineseHoliday():
    @property
    def english_to_chinese(self):
        return {
            "New Year's Day": "元旦",
            "Spring Festival": "春节",
            "Tomb-sweeping Day": "清明节",
            "Labour Day": "劳动节",
            "Dragon Boat Festival": "端午节",
            "Mid-Autumn Festival": "中秋节",
            "National Day": "国庆节",
            "Anti-Fascist 70th Day": "抗战胜利70周年纪念日",
        }

    def get_chinese_from_english(self, english):
        if english in self.english_to_chinese:
            return self.english_to_chinese[english]
        else:
            return english