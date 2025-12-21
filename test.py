from math import ceil

class Solution:
    def minEatingSpeed(self, piles, h: int) -> int:
        if len(piles) == 1: return piles[0]
        right = max(piles)
        left = 1

        best_k = float('inf')
        while left <= right:
            mid = (right + left) // 2
            hrs = self.eating_time(mid, piles)

            if hrs <= h:
                best_k = min(best_k, mid)
                right = mid - 1
            else:
                left = mid + 1
        
        return best_k

    @staticmethod
    def eating_time(k, piles):
        hr = 0
        for p in piles:
            hr += ceil(p / k)
        
        return hr
    
print(Solution().minEatingSpeed([30,11,23,4,20], 5))