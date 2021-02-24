#ifndef INTERN_HPP
#define INTERN_HPP

#include <climits>
#include <functional>
#include <memory>
#include <mutex>
#include <tuple>
#include <unordered_map>
#include <utility>

namespace intern {

	template<typename T, typename... Ts>
		constexpr auto Hash(const T& v, const Ts&... vs) -> std::size_t {
			if constexpr(sizeof...(Ts) == 0) {
				return std::hash<T>{}(v);
			}
			else {
				constexpr std::size_t kMagic =
					sizeof(std::size_t) * CHAR_BIT > 32u ?
					0x9e3779b97f4a7c15 : 0x9e3779b9;
				auto h = Hash(vs...);
				return h ^ (Hash(v) + kMagic + (h << 6) + (h >> 2));
			}
		}

	namespace details {
		struct TupleHash {
			std::size_t mHash;
			template<typename... Args>
				constexpr TupleHash(const Args&... args):
					mHash{Hash(args...)} {}
		};
	}

	template<typename Tuple>
		constexpr auto HashTuple(const Tuple& tuple) {
			return std::make_from_tuple<details::TupleHash>(tuple).mHash;
		}

	constexpr bool kHasHashFn = true;
	template<class Cls, bool HasHashFn>
		class Interned: public Cls {
			template<class Cls2, bool HasHashFn2, typename... Args>
				friend auto MakeInterned(Args&&... args)
					-> std::shared_ptr<const Interned<Cls2,HasHashFn2>>;
			using TInternMap = std::unordered_map<
				const Interned*, std::weak_ptr<const Interned>
				>;
			using TInternMut = std::mutex;
			inline static TInternMap gInternMap;
			inline static TInternMut gInternMut;
		 public:
			using Cls::Cls;
			~Interned() {
					std::lock_guard<TInternMut> lg{gInternMut};
					gInternMap.erase(this);
				}
		};
	template<class Cls, bool HasHashFn=false, typename... Args>
		auto MakeInterned(Args&&... args)
			-> std::shared_ptr<const Interned<Cls,HasHashFn>>
		{
			using TInterned = Interned<Cls,HasHashFn>;
			using TMutex = typename TInterned::TInternMut;
			std::shared_ptr<const TInterned> p;
			TInterned val{std::forward<Args>(args)...};
			std::lock_guard<TMutex> lg{TInterned::gInternMut};
			auto& map = TInterned::gInternMap;
			auto it = map.find(&val);
			if(it == map.end()) {
				p = std::make_shared<const TInterned>(std::move(val));
				map.insert(it, std::make_pair(p.get(), p));
			}
			else {
				p = it->second.lock();
			}
			return std::move(p);
		}
}

namespace std {
	template<typename Cls, bool HasHashFn>
		struct hash<const intern::Interned<Cls,HasHashFn>*> {
			auto operator()(
				const intern::Interned<Cls,HasHashFn>* p)
					const noexcept -> std::size_t
				{
					if constexpr(HasHashFn) {
						return p->hash();
					}
					else {
						return hash<Cls>{}(*p);
					}
				}
		};
}

#endif
