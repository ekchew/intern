#ifndef INTERN_HPP
#define INTERN_HPP

#include <climits>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <tuple>
#include <unordered_map>
#include <utility>

namespace intern {

	enum class kMapType { Unordered, Ordered };

	namespace details {
		template<typename Cls, kMapType MT> struct Interned;
		template<typename Cls, kMapType MT>
			struct Map {
				using Type = std::unordered_map<
					const Cls&,
					std::weak_ptr<const Interned<Cls,kMapType::Unordered>>
					>;
			};
		template<typename Cls>
			struct Map<Cls,kMapType::Ordered> {
				using Type = std::map<
					const Cls&,
					std::weak_ptr<const Interned<Cls,kMapType::Ordered>>
					>;
			};
		template<typename Cls, kMapType MT>
			using TMap = typename Map<Cls,MT>::Type;
		template<typename Cls, kMapType MT>
			struct Interned: Cls {
				using TMutex = std::mutex;
				template<typename... Args> static
					auto MakeInterned(Args&&... args)
						-> std::shared_ptr<const Interned>
					{
						using std::move;
						std::shared_ptr<const Interned> p;
						Cls v{std::forward<Args>(args)...};
						std::lock_guard<TMutex> lg{gInternMapMutex};
						auto it = gInternMap.find(v);
						if(it == gInternMap.end()) {
							p = std::make_shared<const Interned>(move(v));
							gInternMap.insert(it, std::make_pair(*p, p));
						}
						else {
							p = it->second.lock();
						}
						return move(p);
					}
				using Cls::Cls;
				~Interned() {
					std::lock_guard<TMutex> lg{gInternMapMutex};
					gInternMap.erase(*this);
				}
			private:
				inline static TMap<Cls,MT> gInternMap;
				inline static TMutex gInternMapMutex;
			};
	}

	template<typename Cls, kMapType MT = kMapType::Unordered, typename... Args>
		auto MakeInterned(Args&&... args)
			-> std::shared_ptr<const details::Interned<Cls,MT>>
		{
			return details::Interned<Cls,MT>::MakeInterned(
				std::forward<Args>(args)...
				);
		}

	template<typename T> constexpr
		auto Hash(const T& v) -> std::size_t {
			return std::hash<T>{}(v);
		}
	template<typename T, typename... Ts> constexpr
		auto Hash(const T& v, const Ts&... vs) -> std::size_t {
			constexpr std::size_t kMagic =
				sizeof(std::size_t) * CHAR_BIT > 32u ?
				0x9e3779b97f4a7c15 : 0x9e3779b9;
			constexpr auto h = Hash(vs...);
			return h ^ (Hash(v) + kMagic + (h << 6) + (h >> 2));
		}
	template<typename Tuple>
		auto HashTuple(const Tuple& tuple) {
			return std::apply(Hash, tuple);
		}
}

#endif
